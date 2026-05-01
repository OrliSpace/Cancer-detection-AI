🩺 MONAILabel Remote PET/CT Segmentation Guide

This repository provides a step-by-step workflow for connecting a local 3D Slicer instance to a remote GPU-accelerated HPC server at Bar-Ilan University for medical imaging segmentation.

🛠️ Phase 1: Local Installation & Setup
1. VPN Connection

Install and connect to FortiClient VPN using university credentials.

2. 3D Slicer

Download: https://download.slicer.org/

Use Stable Version (not preview).

3. MONAILabel Extension

In 3D Slicer:

Extensions Manager → Search: MONAILabel
Install → Restart Slicer
🚀 Phase 2: Remote Server Configuration (HPC)
1. Login + GPU Node
ssh <YOUR_USERNAME>@slurm-login2.lnx.biu.ac.il

Then request compute node:

srun --pty -c 4 --mem=16G --gres=gpu:1 --partition=L4-4h bash

After this you will see something like:

hpc8l4-01

This is your COMPUTE NODE.

2. Start MONAILabel Server (on compute node)
cd /home/dsi/<YOUR_USERNAME>/dicom_project/

source ~/venvs/nnunet_v1_legacy/bin/activate

monailabel start_server \
  --app apps/radiology \
  --studies /home/dsi/<YOUR_USERNAME>/dicom_project/OB_NIFTI_FIXED \
  --host 0.0.0.0 \
  --port 8000 \
  --conf models deepedit

Wait until you see:

Uvicorn running on http://0.0.0.0:8000
🌉 Phase 3: SSH Tunnel (Local Machine)

Open NEW PowerShell on your PC:

ssh -J <YOUR_USERNAME>@slurm-login2.lnx.biu.ac.il ^
-L 9007:localhost:8000 ^
<YOUR_USERNAME>@hpc8l4-01

⚠️ Replace hpc8l4-01 with your actual compute node if different.

Keep this window open.

🖥️ Phase 4: 3D Slicer Connection

In MONAILabel module inside Slicer:

http://127.0.0.1:9007

Then:

Click Refresh
Load model
Click Next Sample
🆘 Troubleshooting
Issue	Fix
Address already in use	Change port 9007 → 9008 everywhere
No route to host	Wrong compute node or VPN disconnected
Connection refused	Server not running or wrong port
Slicer not connecting	Rebuild SSH tunnel
