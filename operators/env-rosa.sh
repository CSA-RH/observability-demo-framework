export CLUSTER_NAME=$(oc get infrastructure cluster -o=jsonpath="{.status.apiServerURL}" | awk -F '.' '{print $2}')
export HYPERSCALER_STORAGE_SECRET_TYPE=s3
export HYPERSCALER_STORAGE_CLASS=gp3-csi
export AWS_PAGER=""

# Get Loki bucket in S3
get_aws_bucket() {
    local BUCKET_IDENTIFIER="$1"
    TAG_KEY="observability-demo-framework"
    TAG_VALUE="$BUCKET_IDENTIFIER"
    BUCKET_PREFIX="obs-demo-framework-$CLUSTER_NAME-$BUCKET_IDENTIFIER"

    # Check existing buckets
    if bucket=$(aws s3api list-buckets --query "Buckets[?starts_with(Name, '$BUCKET_PREFIX')].Name" --output text | head -n 1) && [ -n "$bucket" ]; then
      echo "$bucket"
      return 0    
    fi

    # No existing bucket found, create a new one
    RANDOM_SUFFIX=$(openssl rand -hex 4)
    NEW_BUCKET="${BUCKET_PREFIX}-${RANDOM_SUFFIX}"

    # Create the bucket
    aws s3api create-bucket --bucket "$NEW_BUCKET" --region "$(aws configure get region)" --create-bucket-configuration LocationConstraint="$(aws configure get region)" >/dev/null

    # Tag the bucket
    aws s3api put-bucket-tagging --bucket "$NEW_BUCKET" --tagging "TagSet=[{Key=$TAG_KEY,Value=$TAG_VALUE}]" >/dev/null

    echo "$NEW_BUCKET"
}

get_aws_tempo_bucket() {
  echo $(get_aws_bucket "tempo")
  return 0
}

get_aws_loki_bucket(){
  echo $(get_aws_bucket "loki")
  return 0
}

load_environment_storage_backend(){
  export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
  export AWS_REGION=$(oc get infrastructure cluster -o=jsonpath="{.status.platformStatus.aws.region}" | tr -d '[:space:]')
  export OIDC_ENDPOINT=$(oc get authentication.config.openshift.io   cluster \
    -o jsonpath='{.spec.serviceAccountIssuer}' | sed  's|^https://||')
}

load_tempo_storage_backend() {
  load_environment_storage_backend  
  export TEMPO_BUCKET=$(get_aws_tempo_bucket)
  echo "  [Tempo] AWS S3 Bucket: $TEMPO_BUCKET"
  AWS_S3_TEMPO_IAM_ROLE="${CLUSTER_NAME}-tempostack-access-role"
  if aws iam get-role --role-name $AWS_S3_TEMPO_IAM_ROLE --query "Role.RoleName" --output text 2>/dev/null; then
    echo "  [Tempo]  IAM role $AWS_S3_TEMPO_IAM_ROLE exists"
    export TEMPO_ROLE_ARN=$(aws iam get-role --role-name $AWS_S3_TEMPO_IAM_ROLE --query 'Role.Arn' --output text | tr -d '\n')
  else
    POLICY_ARN=arn:aws:iam::aws:policy/AmazonS3FullAccess
    echo "  [Tempo]  IAM policy to adopt: $POLICY_ARN (TODO: restrict to the bucket)"
    cat <<EOF > /tmp/trust-policy.json
{
   "Version": "2012-10-17",
   "Statement": [
   {
   "Effect": "Allow",
   "Condition": {
     "StringEquals" : {
       "${OIDC_ENDPOINT}:sub": ["system:serviceaccount:$CURRENT_NAMESPACE:tempo-escotilla"]
      }
    },
    "Principal": {
     "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_ENDPOINT}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity"
    }
    ]
}
EOF
    TEMPO_ROLE_ARN=$(aws iam create-role --role-name $AWS_S3_TEMPO_IAM_ROLE \
      --assume-role-policy-document file:///tmp/trust-policy.json \
      --query Role.Arn --output text)
    echo "  [Tempo]  IAM role created: $TEMPO_ROLE_ARN"
    aws iam attach-role-policy \
      --policy-arn $POLICY_ARN \
      --role-name $AWS_S3_TEMPO_IAM_ROLE
    echo "  [Tempo]  IAM policy ARN $POLICY_ARN attached to the role $AWS_S3_TEMPO_IAM_ROLE"    
  fi
  cat <<EOF | oc apply -f -
kind: Secret
apiVersion: v1
metadata:
  name: tempo-storage-secret
  namespace: $CURRENT_NAMESPACE
data:
  bucket: $(echo -n $TEMPO_BUCKET | base64 -w 0)
  region: $(echo -n $AWS_REGION | base64 -w 0)
  audience: $(echo -n openshift | base64 -w 0)
  role_arn: $(echo -n $TEMPO_ROLE_ARN | base64 -w 0)
type: Opaque
EOF
}

load_loki_storage_backend() {
  load_environment_storage_backend
  # From https://cloud.redhat.com/experts/o11y/openshift-logging-lokistack/
  export LOKI_BUCKET=$(get_aws_loki_bucket)
  echo "  [Loki] AWS S3 Bucket: $LOKI_BUCKET"
  # Check specific IAM role
  AWS_S3_LOKI_IAM_ROLE="${CLUSTER_NAME}-lokistack-access-role"
  if aws iam get-role --role-name $AWS_S3_LOKI_IAM_ROLE --query "Role.RoleName" --output text 2>/dev/null; then
    echo "  [Loki]  IAM role $AWS_S3_LOKI_IAM_ROLE exists"
  else    
    cat <<EOF > /tmp/policy.json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LokiStorage",
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket",
                "s3:PutObject",
                "s3:GetObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "arn:aws:s3:::${LOKI_BUCKET}",
                "arn:aws:s3:::${LOKI_BUCKET}/*"
            ]
        }
    ]
}
EOF
    POLICY_ARN=$(aws --region "$AWS_REGION" --query Policy.Arn \
      --output text iam create-policy \
      --policy-name "$CLUSTER_NAME-lokistack-access-policy" \
      --policy-document file:///tmp/policy.json)
    echo "  [Loki]  IAM policy created: $POLICY_ARN"
    cat <<EOF > /tmp/trust-policy.json
{
   "Version": "2012-10-17",
   "Statement": [
   {
   "Effect": "Allow",
   "Condition": {
     "StringEquals" : {
       "${OIDC_ENDPOINT}:sub": ["system:serviceaccount:openshift-logging:loki"]
      }
    },
    "Principal": {
     "Federated": "arn:aws:iam::${AWS_ACCOUNT_ID}:oidc-provider/${OIDC_ENDPOINT}"
    },
    "Action": "sts:AssumeRoleWithWebIdentity"
    }
    ]
}
EOF
    export LOKI_ROLE_ARN=$(aws iam create-role --role-name $AWS_S3_LOKI_IAM_ROLE \
      --assume-role-policy-document file:///tmp/trust-policy.json \
      --query Role.Arn --output text)
    echo "  [Loki]  IAM role created: $LOKI_ROLE_ARN"
    aws iam attach-role-policy \
      --policy-arn $POLICY_ARN \
      --role-name $AWS_S3_LOKI_IAM_ROLE
    echo "  [Loki]  IAM policy ARN $POLICY_ARN attached to the role $AWS_S3_LOKI_IAM_ROLE"    
  fi
}


install_loki_subscription() {
  cat <<EOF | oc apply -f - 
kind: Secret
apiVersion: v1
metadata:
  name: loki-storage-secret
  namespace: openshift-logging
data:
  bucketnames: $(echo -n $LOKI_BUCKET | base64 -w 0)
  region: $(echo -n $AWS_REGION | base64 -w 0)
  audience: $(echo -n openshift | base64 -w 0)  
type: Opaque
EOF
    cat <<EOF | oc apply -f -
apiVersion: operators.coreos.com/v1alpha1
kind: Subscription
metadata:    
  labels:
    operators.coreos.com/loki-operator.openshift-loki-operator: ""
    observability-demo-framework: 'operator'
  name: loki-operator
  namespace: openshift-loki-operator
spec:
  channel: stable-6.1
  installPlanApproval: Automatic
  name: loki-operator
  source: redhat-operators
  sourceNamespace: openshift-marketplace
  startingCSV: loki-operator.v6.1.8
  config:
    env:
    - name: ROLEARN
      value: $LOKI_ROLE_ARN
EOF
}
