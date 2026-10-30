cat <<EOF | oc create -f -
apiVersion: batch/v1
kind: Job
metadata:
  generateName: minio-buckets-
  labels: 
    observability-demo-framework: bootstrap
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 180  
  template:
    spec:      
      containers:
      - name: minio-bootstrap
        image: cgr.dev/chainguard/minio:latest
        command: ["/bin/sh", "/runner/create-bucket.sh"]
        env: 
        - name: MINIO_ROOT_USER
          valueFrom:
            secretKeyRef: 
              name: minio-credentials 
              key: user
        - name: MINIO_ROOT_PASSWORD
          valueFrom:
            secretKeyRef: 
              name: minio-credentials 
              key: password
        volumeMounts:
        - name: runner-vol
          mountPath: /runner
      restartPolicy: Never
      volumes: 
      - name: runner-vol
        configMap:
          name: script-bucket-creation
          defaultMode: 0555
EOF