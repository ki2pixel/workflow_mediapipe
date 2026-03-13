# AWS ECR[](#aws-ecr)

To deploy a private [AWS ECR](https://aws.amazon.com/ecr/) image, make sure the ECR is authorized to the AWS account you've connected to Lightning. Once that happens, use the name and tag when starting the deployment.

`1 ` ` $AWS_ACCOUNT_ID.dkr.ecr.$LIGHTNING_CLUSTER_PRIMARY_REGION.amazonaws.com/litserve-model:latest`

Note: Private AWS ECR deployments are only available on the enterprise tier when connected to your AWS account.

