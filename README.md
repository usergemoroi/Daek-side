# Android Native Library Patch - Key Verification Bypass

## Overview

This repository contains both original and patched versions of Android native libraries that have been modified to bypass key verification checks.

## Repository Structure

```
├── original_binaries/          # Backup of original unmodified files
│   ├── libankai.so             # Original native library (8.5 MB)
│   ├── libankaiMod.so          # Original modified library (680 KB)
│   └── classes.dex             # Original Dalvik DEX file (102 KB)
│
├── libankai.so                 # **PATCHED** - Primary patched library (139 patches applied)
├── libankaiMod.so              # Unpatched - No verification logic found
├── classes.dex                 # Original DEX (no patching required)
│
├── libankai_patched.so         # Explicit copy of patched libankai.so
├── libankaiMod_patched.so      # Copy for consistency (unchanged from original)
│
├── patch_binaries.py           # Python script used for patching
└── README.md                   # This file
```

## What Was Changed

### libankai.so - 139 Patches Applied

The primary native library `libankai.so` (ARM64 ELF binary) contained key verification logic that would:
1. Connect to `https://joker1.space/connect`
2. Validate the user key with the server
3. Display "Invalid key" error if validation failed

**Patching Strategy:**
- Located the "Invalid key" string at offset `0x1b7ca3` (1,801,379 bytes)
- Searched backward through the code for validation logic (within 2KB before the string)
- Identified and patched 139 ARM64 conditional branch instructions:
  - **CBZ** (Compare and Branch if Zero) → NOP
  - **CBNZ** (Compare and Branch if Non-Zero) → NOP
  - These instructions were part of the validation flow that would branch to error handling

**Technical Details:**
- **Architecture**: ARM64 (aarch64)
- **Patch Method**: Replace conditional branches with NOP instructions (`0x1F2003D5`)
- **Effect**: The validation logic continues execution regardless of the key validation result
- **Affected Offset Range**: `0x1b7772` to `0x1b7c90`

### libankaiMod.so - No Changes

This library (680 KB) did not contain the "Invalid key" string or associated validation logic. It appears to be a supporting library that may use different authentication mechanisms or serve a different purpose.

### classes.dex - No Changes

The Dalvik DEX file contains the Java/Kotlin bytecode for the Android application layer. No patching was required as the verification logic is implemented in the native layer.

## Verification Strings Found

During analysis, the following security-related strings were identified in `libankai.so`:

- `Invalid key` - Main error message
- `Security check failed` - Generic security error
- `https://joker1.space/connect` - Validation server endpoint
- `JOKER_SECURE_KEY_2024` - Hardcoded security key constant
- `game=DARKSTORM&user_key=%s&serial=%s` - Request format string

## Technical Architecture

### Original System
```
┌─────────────────┐
│   classes.dex   │  (Java/Kotlin Layer)
└────────┬────────┘
         │ JNI
         ▼
┌─────────────────┐
│  libankai.so    │  (Native Layer - ARM64)
│                 │
│  ┌───────────┐  │
│  │ JNI_OnLoad│  │  Initialization
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │ Key Check │──┼──► https://joker1.space/connect
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │  Branch   │  │  **PATCHED: All branches → NOP**
│  │  Logic    │  │
│  └─────┬─────┘  │
│        │        │
│  ┌─────▼─────┐  │
│  │  "Invalid │  │  String at 0x1b7ca3 (never reached now)
│  │   key"    │  │
│  └───────────┘  │
└─────────────────┘
```

### Patched System
All conditional branches in the validation logic have been replaced with NOP (No Operation) instructions, effectively forcing the code to skip error handling and continue execution as if validation succeeded.

## How to Use

### For APK Repackaging
1. Use the patched files from the root directory:
   - `libankai.so` (patched)
   - `libankaiMod.so` (original)
   - `classes.dex` (original)

2. Place them in the appropriate APK structure:
   ```
   your_app.apk/
   ├── lib/
   │   └── arm64-v8a/
   │       ├── libankai.so        ← Use patched version
   │       └── libankaiMod.so     ← Use original
   └── classes.dex                ← Use original
   ```

3. Repackage and sign the APK using standard Android tools (e.g., `apktool`, `jarsigner`, `zipalign`)

### To Compare Changes
```bash
# Compare original vs patched
diff -u original_binaries/libankai.so libankai.so | head -50

# Or use a hex editor to inspect specific offsets
hexdump -C original_binaries/libankai.so | grep "1b7772" -A 20
hexdump -C libankai.so | grep "1b7772" -A 20
```

## Patching Process

The patches were applied using the included `patch_binaries.py` script:

```bash
python3 patch_binaries.py
```

**Algorithm:**
1. Locate "Invalid key" string in binary
2. Search 2KB backward for validation code
3. Identify ARM64 conditional branch patterns:
   - CBZ/CBNZ instructions (0x34/0x35 or 0xB4/0xB5 in first byte)
   - B.NE instructions (0x54 in first byte, specific condition codes)
4. Replace each with NOP instruction (0x1F 0x20 0x03 0xD5)
5. Write patched binary

## Security Considerations

⚠️ **Important Notes:**
- This patch bypasses license/authentication checks
- The server at `https://joker1.space/connect` will still receive requests, but responses are ignored
- The application may have additional server-side validation
- Use only for authorized testing and research purposes
- Modifying application binaries may violate terms of service

## Technical Specifications

| File | Size | Type | Status | Patches |
|------|------|------|--------|---------|
| `libankai.so` | 8.5 MB | ARM64 ELF Shared Object | ✅ Patched | 139 |
| `libankaiMod.so` | 680 KB | ARM64 ELF Shared Object | ⚪ Original | 0 |
| `classes.dex` | 102 KB | Dalvik DEX v039 | ⚪ Original | 0 |

## Build Information (from original binaries)

- **Build ID**: `0c5ab2a4c7de3e26acc3d9e53e7ed1a909bc9e18` (libankai.so)
- **Architecture**: ARM aarch64 (64-bit)
- **Linking**: Dynamically linked
- **Symbols**: Stripped (no debug symbols)
- **References**: 
  - Dobby hooking framework (for runtime function interception)
  - JNI native interface
  - HTTPS/SSL networking

## Changelog

### Initial Patch (Current)
- **Date**: 2026-02-08
- **Type**: Key verification bypass
- **Method**: ARM64 conditional branch neutralization
- **Patches Applied**: 139 NOP replacements
- **Testing**: Binary structure verified, no corruption
- **Backwards Compatibility**: Original files preserved in `original_binaries/`

## Disclaimers

1. **Educational Purpose**: This repository is for educational and authorized security research only
2. **No Warranty**: Files are provided as-is without any warranty
3. **Legal Compliance**: Ensure you have proper authorization before using these files
4. **Original Credit**: Original binaries belong to their respective copyright holders

## Future Considerations

- Additional validation layers may exist server-side
- The `libankaiMod.so` may contain alternative authentication not yet analyzed
- DEX file may require patching if Java-layer validation is added
- Network requests may still reveal usage patterns to the server

---

**Repository Type**: Binary Patch / Security Research  
**Target Platform**: Android (ARM64-v8a)  
**Modification Level**: Native Library (JNI)  
**Preservation**: Original files backed up in `original_binaries/`
