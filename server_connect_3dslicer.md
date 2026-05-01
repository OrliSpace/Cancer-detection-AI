
# 🩺 MONAILabel Remote PET/CT Segmentation Guide

This guide provides a standardized workflow for connecting a local **3D Slicer** instance to a remote **GPU-accelerated HPC server** at Bar-Ilan University.

---

## 🛠️ Prerequisites & Installation

Before starting, ensure the following setup is completed on your local machine:

*   **VPN Connection**: Connect to the **FortiClient VPN** using your university credentials. 
*   **3D Slicer**: Install the [Stable Version](https://download.slicer.org/) of 3D Slicer.
*   **MONAILabel Extension**:
    1.  Open **3D Slicer**.
    2.  Go to the **Extensions Manager** (blue box icon).
    3.  Search for **MONAILabel**.
    4.  Click **Install** and **Restart** Slicer.

---

## 🚀 Step 1: Resource Allocation (HPC Terminal)

Connect to the Login node and request a compute node with a GPU.

```bash
# 1. Connect to the Login node
ssh <YOUR_USERNAME>@slurm-login2.lnx.biu.ac.il

# 2. Request a GPU node (Example: L4 partition)- need to be changed when have the exact gpu usage
srun --pty -c 4 --mem=16G --gres=gpu:1 --partition=L4-4h bash
```

> **Note**: Take note of the assigned node name in your prompt (e.g., `hpc8l4-01`). This is your **`<NODE_NAME>`**.

---

## 🛰️ Step 2: Start MONAILabel Server (HPC Terminal)

Once inside the compute node, initialize the project and start the server.

```bash
# 1. Navigate to the project directory
cd /home/dsi/<YOUR_USERNAME>/dicom_project/

# 2. Activate the virtual environment
source ~/venvs/nnunet_v1_legacy/bin/activate

# 3. Launch the MONAILabel server
monailabel start_server --app apps/radiology --studies /home/dsi/<YOUR_USERNAME>/dicom_project/OB_NIFTI_FIXED --conf models deepedit
```

*   **Wait** until you see: `Uvicorn running on [http://0.0.0.0:8000](http://0.0.0.0:8000)`.

---

## 🌉 Step 3: Establish the Tunnel (Local PowerShell)

Open a **New PowerShell** window on your Windows PC. This command uses a **ProxyJump** to bypass internal routing restrictions.

```powershell
# Replace <YOUR_USERNAME> and <NODE_NAME> accordingly
ssh -J <YOUR_USERNAME>@slurm-login2.lnx.biu.ac.il -L 9007:localhost:8000 <YOUR_USERNAME>@<NODE_NAME>
```

*   **Important**: Keep this PowerShell window **open** during your entire session.
*   If prompted for a password, enter your BIU password (you may be asked twice).

---

## 🖥️ Step 4: Connect 3D Slicer

1.  Open **3D Slicer** and select the **MONAILabel** module.
2.  In the **MONAI Label server** field, paste one of the above:
    `http://127.0.0.1:9007`
    `http://127.0.0.1:9007`
4.  Click the **Refresh** button (circular arrows).
5.  Verify that **App Name** and **Models** are populated.
6.  Click **Next Sample** to start labeling.

---

## 🆘 Troubleshooting

*   **Address already in use**: 
    *   Change `9007` to `9008` in both the PowerShell command and Slicer address.
*   **No route to host**: 
    *   Ensure the VPN is active.
    *   Verify the `<NODE_NAME>` is correct by typing `hostname` in the HPC terminal.
*   **Connection Reset (10054)**: 
    *   The VPN or the HPC session has timed out. Restart Step 1 and Step 3.
*   **Invalid IPv6 URL**: 
    *   Do not include brackets `[]` or spaces in the Slicer server field.

---
*Developed for the Bar-Ilan University CS Excellence Program by Roei Kadosh
