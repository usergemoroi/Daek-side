#!/usr/bin/env python3
"""
Binary patcher to bypass key verification in Android native libraries
This script patches the validation logic to always return success
"""

import os
import sys

def find_pattern(data, pattern):
    """Find all occurrences of a pattern in binary data"""
    positions = []
    pos = 0
    while True:
        pos = data.find(pattern, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += 1
    return positions

def patch_library(input_file, output_file):
    """
    Patch the native library to bypass key verification.
    Strategy: Find code that references "Invalid key" and patch
    the branch/conditional logic that leads to it.
    """
    print(f"[*] Reading {input_file}...")
    with open(input_file, 'rb') as f:
        data = bytearray(f.read())
    
    original_size = len(data)
    print(f"[*] File size: {original_size} bytes")
    
    # Find the "Invalid key" string
    invalid_key_str = b"Invalid key"
    positions = find_pattern(data, invalid_key_str)
    
    if not positions:
        print(f"[!] Could not find 'Invalid key' string in {input_file}")
        return False
    
    print(f"[*] Found 'Invalid key' string at offset(s): {[hex(p) for p in positions]}")
    
    # ARM64 instruction patterns to look for near the string reference
    # We'll patch conditional branches to unconditional or NOP them
    # Common ARM64 patterns:
    # - B.NE (branch if not equal): 0x54...01 (last byte varies)
    # - CBZ (compare and branch if zero): 0x...B4 / 0x...34
    # - CBNZ (compare and branch if not zero): 0x...B5 / 0x...35
    
    patches_made = 0
    
    # Search backwards from the string reference to find validation code
    # Typically within 2KB before the string
    for string_pos in positions:
        search_start = max(0, string_pos - 2048)
        search_end = string_pos
        
        print(f"[*] Searching for validation logic near offset {hex(string_pos)}...")
        
        # Look for common ARM64 conditional branch patterns
        # Pattern 1: CBZ/CBNZ instructions (Compare and Branch if Zero/Non-Zero)
        for i in range(search_start, search_end - 4):
            instruction = data[i:i+4]
            
            # Check for CBNZ (Compare and Branch if Non-Zero)
            # Format: xxx1 01x1 xxxx xxxx xxxx xxxx (0x35 or 0xB5 in byte 0)
            if len(instruction) == 4 and (instruction[0] & 0x7F) in [0x35, 0x75]:
                # Patch: Replace CBNZ with NOP (0x1F2003D5)
                print(f"[+] Found CBNZ at offset {hex(i)}, patching to NOP")
                data[i:i+4] = b'\x1f\x20\x03\xd5'  # NOP instruction
                patches_made += 1
            
            # Check for B.NE (Branch if Not Equal)
            # Format: 0101 0100 xxxx xxxx xxxx xxxx xxx0 0001
            if len(instruction) == 4 and instruction[0] == 0x54 and (instruction[3] & 0x0F) == 0x01:
                # Patch: Change B.NE to B (unconditional branch) or NOP
                # For bypass, we change to NOP so execution continues
                print(f"[+] Found B.NE at offset {hex(i)}, patching to NOP")
                data[i:i+4] = b'\x1f\x20\x03\xd5'  # NOP instruction
                patches_made += 1
            
            # Check for CBZ (Compare and Branch if Zero)  
            # Format: xxx1 00x1 xxxx xxxx xxxx xxxx (0x34 or 0xB4 in byte 0)
            if len(instruction) == 4 and (instruction[0] & 0x7F) in [0x34, 0x74]:
                # This might be checking for success (==0), so we might want to keep it
                # But if it's checking for failure, patch it
                print(f"[+] Found CBZ at offset {hex(i)}, patching to NOP")
                data[i:i+4] = b'\x1f\x20\x03\xd5'  # NOP instruction
                patches_made += 1
    
    # Alternative approach: Look for functions that return error codes
    # ARM64 pattern for "MOV W0, #0" followed by RET (returns 0/failure)
    # We can change to "MOV W0, #1" to return success
    
    # Pattern: MOV W0, #0 (0x00 0x00 0x80 0x52) followed by RET (0xC0 0x03 0x5F 0xD6)
    mov_w0_0 = b'\x00\x00\x80\x52'
    ret_instr = b'\xc0\x03\x5f\xd6'
    
    for i in range(len(data) - 8):
        if data[i:i+4] == mov_w0_0 and data[i+4:i+8] == ret_instr:
            # Check if this is near our validation code (within 4KB of Invalid key string)
            if any(abs(i - pos) < 4096 for pos in positions):
                # Patch: MOV W0, #1 (returns success)
                print(f"[+] Found 'MOV W0, #0; RET' at offset {hex(i)}, patching to 'MOV W0, #1; RET'")
                data[i:i+4] = b'\x20\x00\x80\x52'  # MOV W0, #1
                patches_made += 1
    
    if patches_made == 0:
        print(f"[!] No validation logic patterns found to patch in {input_file}")
        print(f"[*] Attempting generic patch: forcing all returns near validation to succeed...")
        
        # More aggressive approach: patch any RET near the Invalid key string
        for string_pos in positions:
            search_start = max(0, string_pos - 1024)
            search_end = min(len(data) - 4, string_pos + 512)
            
            for i in range(search_start, search_end, 4):
                # Look for RET instruction
                if data[i:i+4] == ret_instr:
                    # Check if there's a MOV W0/X0 instruction before it
                    if i >= 4:
                        prev_instr = data[i-4:i]
                        # If previous is MOV W0, #0 or similar, patch it
                        if prev_instr[1:4] == b'\x00\x80\x52':
                            print(f"[+] Patching return value at {hex(i-4)} to return success")
                            data[i-4] = 0x20  # Change to MOV W0, #1
                            patches_made += 1
    
    print(f"[*] Total patches applied: {patches_made}")
    
    if patches_made > 0:
        print(f"[*] Writing patched binary to {output_file}...")
        with open(output_file, 'wb') as f:
            f.write(data)
        print(f"[+] Successfully patched {output_file}")
        return True
    else:
        print(f"[!] No patches applied to {input_file}")
        return False

def main():
    files_to_patch = [
        ('libankai.so', 'libankai.so'),
        ('libankaiMod.so', 'libankaiMod.so'),
    ]
    
    success_count = 0
    
    for input_file, output_file in files_to_patch:
        if not os.path.exists(input_file):
            print(f"[!] File not found: {input_file}")
            continue
        
        print(f"\n{'='*60}")
        print(f"Processing: {input_file}")
        print(f"{'='*60}")
        
        if patch_library(input_file, output_file):
            success_count += 1
            
            # Create additional "_patched" versions for clarity
            patched_name = output_file.replace('.so', '_patched.so')
            os.system(f'cp {output_file} {patched_name}')
            print(f"[+] Created additional copy: {patched_name}")
    
    print(f"\n{'='*60}")
    print(f"Patching complete: {success_count}/{len(files_to_patch)} files patched")
    print(f"{'='*60}")
    
    if success_count > 0:
        print("\n[+] Backup of original files:")
        print("    - original_binaries/libankai.so")
        print("    - original_binaries/libankaiMod.so")
        print("    - original_binaries/classes.dex")
        print("\n[+] Patched files in root directory:")
        print("    - libankai.so (patched)")
        print("    - libankaiMod.so (patched)")
        print("    - libankai_patched.so (copy)")
        print("    - libankaiMod_patched.so (copy)")
    
    return 0 if success_count > 0 else 1

if __name__ == '__main__':
    sys.exit(main())
