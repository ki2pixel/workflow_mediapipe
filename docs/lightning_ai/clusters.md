# Clusters[](#clusters)

Lightning Clusters can be managed both from the UI and from the Lightning SDK.

This guide will take you through monitoring, billing management and more via the SDK.

## Monitoring[](#monitoring)

`K8sCluster ` is the Lightning SDK class that provides an interface to monitor Kubernetes clusters on Lightning. Use this to retrieve cluster metrics, view GPU usage, and analyze resource allocation for efficient workload distribution.

The SDK is automatically available inside Studios. To use the SDK outside a Studio, install it with:

`1 ` ` pip install --upgrade lightning-sdk`

## Get billing usage[](#get-billing-usage)

Use the example below to get the usage metrics for a given cluster.

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 ` ` from lightning_sdk.k8s_cluster import K8sCluster from datetime import datetime, timedelta # Step 1: Initialize the K8sCluster k8s = K8sCluster("your-cluster-name") # Step 2: [Optional] Define the time range end_date = datetime.now() start_date = end_date - timedelta(hours=12) # Step 3: Retrieve billing usage usage_response = k8s.get_billing_usage(start_date=start_date, end_date=end_date, print_data=True) # Step 4: Analyze the results print(f"Total GPU Usage: {usage_response.total_usage}") for hourly_usage in usage_response.hours: print(f"Time: {hourly_usage.time}, Available GPUs: {hourly_usage.available_gpus}, Billed GPUs: {hourly_usage.billed_gpus}")`

Some example output for this script would look like.

`1 2 3 4 5 6 ` ` hour num_gpus num_requested_gpus num_allocated_gpus billed_gpus 0 2025-11-19 12:00:00+00:00 10 8 8 8 1 2025-11-19 13:00:00+00:00 12 10 10 10 Total GPU Usage: 18.0 Time: 2025-11-19 12:00:00, Available GPUs: 10, Billed GPUs: 8 Time: 2025-11-19 13:00:00, Available GPUs: 12, Billed GPUs: 10`

# API Reference[](#api-reference)

## K8sCluster[](#k8scluster)

`1 2 3 4 ` ` from lightning_sdk.k8s_cluster import K8sCluster k8s = K8sCluster("your-cloud-account") usage_response = k8s.get_billing_usage(print_data=True)`

  - ` * *init * *. ` : Creates an client for your Kubernetes cluster

    - ` cloud_account (str) ` : The name of your cloud account

  - ` get_billing_usage ` : Collects your Kubernetes metrics and returns billing usage breakdown

    - ` start_date (Optional[datetime]) ` : start for when to gather from metrics. By default will grab the next 20 hours after the start\_date if no end\_date was used as an argument. If no timezone is on the datetime, a UTC timezone is assumed.

    - ` end_date (Optional[datetime]) ` : end for when to gather from metrics. By default will grab the previous 20 hours before the end\_date if no start\_date was used as an argument. If no timezone is on the datetime, a UTC timezone is assumed.

    - print\_data ` (Optional[bool]) ` : Prints out more detailed usage metrics broken down by hour

    - Returns:

      - ` K8sUsageResponse ` : A metrics object which includes the usage metrics broken down by hour via the ` hours (List[HourlyUsage]) ` property and the ` total_usage (float) ` representing the total GPU.


## K8sUsageResponse[](#k8susageresponse)

These are the following properties of the K8sUsageResponse class.

  - ` total_usage (float) ` : The specific amount of billable gpu usage time being consumed

  - ` hours List[HourlyUsage] ` : A list of HourlyUsage objects which represent the metrics broken down by hourly each of which containing the following properties:

    - * *HourlyUsage: **

      - ` time (datetime) ` : A datetime representing hour interval the time represents

      - ` available_gpus (int) ` : The amount of available gpus within the cluster

      - ` billed_gpus (int) ` : The amount of gpus actually being used within the cluster * * **


