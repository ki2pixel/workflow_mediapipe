# Managed secrets[](#managed-secrets)

Secrets are variables that store sensitive information \(e.g., passwords, API Keys\) essential to operating a software program. Secrets are encrypted and served securely as environment variables in studios at runtime.


Lightning offers both _ * *user * *_and_ * *teamspace ** _secrets. User secrets are made available as environment variables in all studios the user creates. Teamspace secrets are made available to all studios within the teamspace, regardless of user.

https://pl-bolts-doc-images.s3.us-east-2.amazonaws.com/Docs\_Studios\_MP4/Security-SecurityFeatures-Secrets.mp4

Add a _teamspace_ secret and use as an environment variable

## Teamspace secrets[](#teamspace-secrets)

Teamspace secrets are made available as environment variables in all studios in the teamspace. To create one, navigate to the teamspace and click Settings => Secret => New Secret.

## User secrets[](#user-secrets)

User secrets are made available as environment variables in all studios the user creates. To create one, navigate to your profile at the top right and click Global settings => Secrets => New Secret.

## Use cases[](#use-cases)

Below are a few examples of items that should be stored as secrets instead of hard-coded into your code:

  1. * *API keys: ** Unique identifiers used to authenticate applications using APIs.

  2. * *Encryption keys: ** Keys used in cryptographic algorithms to encrypt and decrypt data.

  3. * *Database credentials ** : Username and password combinations used to access and manage databases.

  4. * *Configuration secrets ** : Sensitive information used in the configuration of software or systems, such as network passwords, SSH keys, or service credentials.

  5. * *Access tokens: ** Tokens used to grant temporary access to an online service. These are often used in web applications for session management and authentication.


## Create a secret[](#create-a-secret)

To create a secret, navigate to the settings page in your Teamspace. Click on "Secrets" in the navigation bar on the left, then "New Secret" in the top right corner. In the dialog that shows up, enter your secret name and the string you want to be encrypted. Upon pressing "Create" your new secret will be stored encrypted in our system and be available to you in every Studio inside your Teamspace.


Select an Image

## Access a secret[](#access-a-secret)

After you created the secret, start a Studio and access the value through the environment variable. Lightning offers both User-level and Teamspace-level secrets.


Environment variables are specified by the Dollar-sign \($\) followed by the variable's name. To use the MY\_SECRET\_PASSWORD variable, you would specify it with $MY\_SECRET\_PASSWORD

Select an Image

If a terminal was open when you added a secret, restart it or open a new one to make the secret visible.

## How secrets are stored[](#how-secrets-are-stored)

Lightning AI * *never stores secrets in plain text * *. Instead, they are securely encrypted before being stored and will only ever be decrypted while being used inside a studio. Lightning offers both User-level and Teamspace-level secrets.

For security, Lightning AI doesn't allow you to view the content of a secret for modification but requires you to reenter the entire secret value instead.

