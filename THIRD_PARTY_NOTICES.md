# Third-Party Notices

UV Studio includes or interoperates with third-party software. This file tracks code that is actually vendored or distributed with UV Studio; research references alone are not automatically dependencies.

## VideoClaw

Project: `HITsz-TMG/VideoClaw`  
License: MIT  
Pinned source revision: `5a16ae23a4f1cb6886c44c0205f7b7e52a34c276`  
Vendored subtree: `video-claw/video-claw`

The vendoring tool writes the exact upstream license to:

`vendor/videoclaw-app/UPSTREAM_LICENSE`

and provenance metadata to:

`vendor/videoclaw-app/.uv-upstream.json`.

The upstream copyright and permission notice must be retained when distributing substantial portions of VideoClaw-derived code.

## External/optional integrations

OpenClaw, `musical-mv-storyboard`, FFmpeg and future media/AI tools require their own license review before bundling. Being mentioned in architecture documents does not mean their code is currently included in this repository.

## Model licenses

Source-code licenses do not automatically cover model weights, datasets, hosted APIs or generated assets. Any model bundled in a future release must have its license/commercial-use/redistribution terms reviewed separately.