# Third-Party Notices

UV Studio includes or interoperates with third-party software. This file tracks code that is actually vendored or intentionally distributed/installed with UV Studio dependency sets; research references alone are not automatically dependencies.

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

## edge-tts (optional)

Project: `rany2/edge-tts`  
UV Studio dependency set: `requirements-edge-tts.txt`  
Supported dependency line: `edge-tts>=7.2.8,<8`  
License metadata: GNU Lesser General Public License v3 (LGPLv3)

UV Studio does not vendor `edge-tts` source in this repository and does not install it through the core `requirements-uv.txt`. It is an optional runtime dependency for the exact `native_videoclaw.edge_tts` compatibility offer.

The `edge-tts` software license covers that client software; it does not by itself grant rights or guarantees for Microsoft-hosted services, generated content, regional availability, or commercial use of a third-party service. Those external service terms must be reviewed separately when relevant.

## External/optional integrations

OpenClaw, `musical-mv-storyboard`, FFmpeg and future media/AI tools require their own license review before bundling. Being mentioned in architecture documents does not mean their code is currently included in this repository.

## Model and hosted-service terms

Source-code licenses do not automatically cover model weights, datasets, hosted APIs/services or generated assets. Any model bundled in a future release must have its license/commercial-use/redistribution terms reviewed separately, and any hosted service used by an adapter must be evaluated under that service's applicable terms rather than inferred from the adapter library's source-code license.
