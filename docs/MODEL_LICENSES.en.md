# Model Files and Distribution Policy

This repository does not contain model weights. Model files may be distributed separately from source code, so the source-code license alone must not be treated as permission to redistribute a checkpoint.

| Component | Current official statement | Repository policy |
| --- | --- | --- |
| AV-CASS source | The official repository's `LICENSE.txt` is the MIT License. | Retain the original notice when using the source. |
| AV-CASS checkpoint | The official README links to a download, but no separate checkpoint redistribution terms are stated. | The installer downloads it on the user's PC from the Google Drive location identified by the project. It is not included in this repository or the public installer. Confirm the permitted scope of automatic downloading with the rights holder before public distribution. |
| CAVP / Diff-Foley | The official Hugging Face model page identifies the model as MIT-licensed. | The installer downloads it from a pinned official Hugging Face commit, verifies SHA-256, and manages it separately from the AV-CASS checkpoint. |
| AudioSep and BandIt | Their official source repositories identify their source licenses as MIT and Apache-2.0 respectively; this repository contains only compatibility workers and no weights. | Recheck the source and weight terms for the exact versions before including them in a distribution. |

## Checks before a public release

1. Finalize the exact code, model, DLL, and EXE inventory included in the distribution.
2. Record each official source URL and exact version or commit.
3. Check source-code licenses and model-weight terms separately.
4. Include all required license texts, copyright notices, change notices, and source links.
5. Do not include model files in the repository; download them directly to the user's PC from the identified distributor with a pinned URL, expected size, and SHA-256.

This document records the current review status and is not legal advice. Recheck the current terms on each official page immediately before a public release.
