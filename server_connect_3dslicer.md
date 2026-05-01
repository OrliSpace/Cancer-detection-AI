🩺 MONAILabel Remote PET/CT Segmentation Guide
This repository provides a step-by-step workflow for connecting a local 3D Slicer instance to a remote GPU-accelerated HPC server at Bar-Ilan University for medical imaging segmentation.

🛠️ Phase 1: Local Installation & Setup
Before connecting, ensure your local machine has the necessary software:

1. VPN Connection
Install and connect to the FortiClient VPN using your university credentials.

Stable connectivity is required to maintain the SSH tunnel.

2. 3D Slicer
Download and install the Stable Version of 3D Slicer.

Note: Avoid "Preview" versions unless specifically required for compatibility.

3. MONAILabel Extension
To install the extension within 3D Slicer:

Open 3D Slicer.

Navigate to the Extensions Manager (blue box icon in the toolbar or View -> Extensions Manager).

Search for MONAILabel.

Click Install, then Restart Slicer when prompted.

🚀 Phase 2: Remote Server Configuration (HPC)
1. Resource Allocation
Connect to the Login node and request a GPU-enabled compute node:

Bash
# Connect to the Login node
ssh <YOUR_USERNAME>@slurm-login2.lnx.biu.ac.il

# Request a GPU node (e.g., L4 partition for 4 hours)
srun --pty -c 4 --mem=16G --gres=gpu:1 --partition=L4-4h bash
Important: Note the assigned node name in your terminal prompt (e.g., hpc8l4-01). This is your <NODE_NAME>.

2. Start the MONAILabel Server
Once inside the compute node, initialize the environment and start the service:

Bash
# Navigate to the project directory
cd /home/dsi/<YOUR_USERNAME>/dicom_project/

# Activate the virtual environment
source ~/venvs/nnunet_v1_legacy/bin/activate

# Launch the MONAILabel server
monailabel start_server --app apps/radiology --studies /home/dsi/<YOUR_USERNAME>/dicom_project/OB_NIFTI_FIXED --conf models deepedit
Wait for the log: Uvicorn running on [http://0.0.0.0:8000](http://0.0.0.0:8000).

🌉 Phase 3: The ProxyJump Connection (Local PC)
Due to internal network routing restrictions, we use a ProxyJump to bridge your local PC and the compute node.

Open a New PowerShell window on your local Windows machine.

Execute the following command:

PowerShell
# Replace placeholders with your specific details
ssh -J <YOUR_USERNAME>@slurm-login2.lnx.biu.ac.il -L 9007:localhost:8000 <YOUR_USERNAME>@<NODE_NAME>
-J: Uses the login node as a jump host.

-L: Maps your local port 9007 to the server's port 8000.

Keep this window open. Closing it will terminate the connection to Slicer.

🖥️ Phase 4: Connecting 3D Slicer
In 3D Slicer, switch to the MONAILabel module.

In the MONAI Label server field, manually type:
[http://127.0.0.1:9007](http://127.0.0.1:9007)

Click the Refresh button (circular arrows).

The App Name (e.g., MONAILabel - Radiology) and Models should populate automatically.

Click Next Sample to load the first PET/CT volume for labeling.
