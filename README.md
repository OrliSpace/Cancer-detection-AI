# Cancer-detection-AI
Graduation project for detecting bladder cancer from CT/PET data using AI


## running the sort function on one study :

```bash
python src/sort_sectra.py path_to_dir_in path_to_out
```

Use `--debug` to write a detailed log and print debug messages:

## Batch Processing (Warper)
To run the sorting process on multiple patient folders sequentially, use the warper.py CLI tool. It iterates over all patient directories in the input folder and generates a centralized master_log.txt.

Run on all folders:

```bash
python src/warper.py -i /path/to/input -o /path/to/output -s src\sort_sectra.py
```

Run a test on a limited number of folders (e.g., 3 folders):

```bash
python src/warper.py -i /path/to/input -o /path/to/output -s src\sort_sectra.py -n 3
```

Run with debug logs enabled:

```bash
python src/warper.py -i /path/to/input -o /path/to/output -s src\sort_sectra.py --debug
```


## Running on an HPC Cluster (Slurm)
For processing large datasets on university/academic clusters, use the provided submit_sorter.sh bash script to queue the batch job via Slurm.

1. Submit the job to the cluster:
```bash
sbatch submit_sorter.sh
```

2. Check your job status in the queue:
``` bash
squeue -u $USER
```
(Look for R for Running, or PD for Pending).

3. Monitor logs in real-time:
The output will be written to a file named sorter_log_<job_id>.out in your current directory.

```bash
tail -f sorter_log_<job_id>.out
```
4. Cancel a running job (if needed):
```bash
scancel <job_id>
```

## Use Resampling: 

python  .\src\resampling_OB_to_WB.py -i data\nifti -o data\rsmpl
