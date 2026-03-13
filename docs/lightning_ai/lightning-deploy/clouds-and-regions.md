# Clouds and regions[](#clouds-and-regions)

Lightning supports multi-cloud deployments on AWS or GCP with zero setup. Lightning is also working with other cloud providers like Nvidia's DGX cloud as well as offering more affordable machines through the Lightning cloud. Machine options from DGX and the Lightning cloud limited and machines are subject to availability, but prices can be cheaper than GCP and AWS.

Tip: More clouds are being added weekly, [email us to request a cloud](mailto:support@lightning.ai?subject=New%20cloud%20account&body=Hi%2C%20I'd%20like%20to%20request%20support%20for%20cloud%20account%20X.%0A%0AWe%20are%20interested%20in%20%5Bdeploying%2Ftraining%5D%20%5Bmodels%2FAPIs%5D%20for%20%5Bobject%20detection%2Fsummarization%5D%20at%20company%20%5Bx%2Fy%2Fz%5D.) .

# Choose cloud or region[](#choose-cloud-or-region)

Deployments automatically run on the cloud and region with the cheapest instance \(machine\) type you selected. Manually configure it under the * *_advanced > deployment_ ** section when creating or updating a deployment.


Modify the deployment regions at creation time

Select an Image

You can modify the region restrictions after the deployment has been created.


Modify the deployment regions once created

Select an Image

# Deploy to a private cloud \(VPC\)[](#deploy-to-a-private-cloud-vpc)

Users on the enterprise tier can connect their cloud accounts to either AWS or GCP. Private cloud deployments keep all traffic and data private within your VPC. It also lets you use cloud credits cloud commitments and reserved instances.

Visit the [manage cloud account guide](https://lightning.ai/docs/team-management/organizations/manage-organization-clusters) to manage all details of a cloud account like pre-provisioning, cost tags, disk encryption and more..

