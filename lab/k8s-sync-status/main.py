from fastapi import FastAPI, HTTPException, BackgroundTasks
from kubernetes import client, config, watch
import os

app = FastAPI()

# --- Kubernetes Job Configuration ---
# Load k8s config (use incluster_config if running in-pod)
if os.getenv('KUBERNETES_SERVICE_HOST'):
    config.load_incluster_config()
else:
    config.load_kube_config()

batch_v1 = client.BatchV1Api()
JOB_NAMESPACE = "obs-demo" # Change this to your namespace
JOB_LABEL_SELECTOR = "observability-demo-framework=users"

# --- Endpoints ---

@app.get("/api/sync-status")
def get_sync_status():
    """
    Checks the status of jobs with the label 'observability-demo-framework: users'.
    - 'running': If ANY job with this label is active.
    - 'idle': If NO jobs are found, or ALL found jobs are not active (completed/failed).
    """
    try:
        # 1. List all jobs in the namespace that match the label selector
        job_list = batch_v1.list_namespaced_job(
            namespace=JOB_NAMESPACE,
            label_selector=JOB_LABEL_SELECTOR
        )

        # 2. Check if any of them are running
        # We iterate through all jobs found
        for job in job_list.items:
            # job.status.active is the count of running pods for this job.
            # If it's greater than 0, the job is "running".
            if job.status.active and job.status.active > 0:
                # Found at least one running job. The whole system is "running".
                return {"status": "running"}

        # 3. If we get here, it means one of two things:
        #    a) No jobs with that label were found (job_list.items was empty)
        #    b) We looped through all found jobs and NONE of them were active.
        # In both cases, the correct status is "idle".
        return {"status": "idle"}
        
    except client.ApiException as e:
        # Handle potential k8s API errors (e.g., invalid permissions)
        print(f"Error checking k8s job status: {e}")
        raise HTTPException(status_code=500, detail="Error checking k8s job status.")