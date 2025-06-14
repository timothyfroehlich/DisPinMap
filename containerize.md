### **Project Update To-Do List: Deploying Discord Bot to GCP**

**Objective:** Modify the existing Python Discord bot to be deployable on Google Cloud Platform (GCP) using Cloud Run and Cloud SQL (PostgreSQL), managed by Terraform. The application must retain its ability to run locally using the current SQLite setup and a .env file for secrets.

### **I. Python Application Modifications**

#### **1\. Update requirements.txt**

To support GCP services, you will need to add specific libraries to your requirements.txt file. Ensure the file contains the following packages, in addition to your existing ones like discord.py and sqlalchemy:

* google-cloud-secret-manager
* google-cloud-sql-connector\[pg8000\]

Your final requirements.txt file should look something like this:
discord.py requests python-dotenv sqlalchemy\>=2.0.0 pytest google-cloud-secret-manager google-cloud-sql-connector\[pg8000\]

#### **2\. Modify src/database.py for Dual Database Support**

Update the Database class \_\_init\_\_ method so it can connect to either the local SQLite database or the new Cloud SQL PostgreSQL database. This logic should be controlled by an environment variable, such as DB\_TYPE.

* **If DB\_TYPE is postgres (for GCP):**
  * Use the google-cloud-sql-connector library to establish a secure connection.
  * The connection logic will require the following environment variables, which will be provided by Cloud Run: DB\_INSTANCE\_CONNECTION\_NAME, DB\_USER, DB\_PASS, and DB\_NAME.
  * Create the SQLAlchemy engine using the connector's getconn method as the creator.
* **If DB\_TYPE is sqlite or not set (for local development):**
  * The application should fall back to the existing logic, using create\_engine to connect to the local SQLite file (e.g., sqlite:///pinball\_bot.db).

#### **3\. Modify src/main.py for Secrets and Health Checks**

Discord Token Handling:
Refactor the application's startup logic to securely fetch the Discord token. The application should first attempt to load the token from GCP Secret Manager. If that fails (i.e., when running locally), it should fall back to using the .env file.

1. Check for a DISCORD\_TOKEN\_SECRET\_NAME environment variable.
2. If it exists, use the google-cloud-secret-manager client library to access that secret's value and assign it as the token.
3. If it does not exist, use python-dotenv to load the .env file and get the DISCORD\_BOT\_TOKEN from the local environment.
4. The application should exit if a token cannot be found in either location.

HTTP Health Check Endpoint:
Cloud Run requires a responsive HTTP endpoint to perform health checks and ensure your container is running correctly. Since the Discord client's run() method is a blocking process, you must refactor the application to run both the bot and a lightweight web server concurrently using asyncio.

1. Import the asyncio and aiohttp libraries.
2. Create an async function (handle\_health\_check) that returns a simple "OK" HTTP response.
3. Create an async task (start\_http\_server\_task) that initializes an aiohttp web application. This server should listen on the host and port provided by the PORT environment variable (standard in Cloud Run).
4. In your main execution block (if \_\_name\_\_ \== '\_\_main\_\_':), get the asyncio event loop.
5. Create and schedule the start\_http\_server\_task.
6. Change the bot startup logic from the blocking client.run(DISCORD\_TOKEN) to the non-blocking await client.start(DISCORD\_TOKEN).
7. Run the main bot task using loop.run\_until\_complete().

#### **4\. Update .gitignore**

To prevent committing sensitive files and local Terraform state to your repository, add the following lines to your .gitignore file:

\# Terraform state files
terraform.tfstate
terraform.tfstate.backup
terraform/.terraform/
\*.tfvars

### **II. Containerization Setup (Dockerfile)**

Create a Dockerfile in the project root. To keep the final image small and secure, use a multi-stage build.

* **Stage 1 (Builder):**
  1. Start from a slim Python base image (e.g., python:3.11-slim-bullseye).
  2. Create and activate a virtual environment (e.g., in /opt/venv).
  3. Copy only the requirements.txt file.
  4. Install the Python dependencies into the virtual environment using pip. This leverages Docker's layer caching.
* **Stage 2 (Final Image):**
  1. Start from the same slim Python base image.
  2. Create a non-root user and group (e.g., appuser) for the application to run as, which is a critical security best practice.
  3. Copy the virtual environment from the builder stage.
  4. Copy the rest of your application source code (e.g., src/ and bot.py).
  5. Set the PATH environment variable to include the virtual environment's bin directory.
  6. Switch to the non-root appuser.
  7. Set the CMD to run your bot's entrypoint script (e.g., python bot.py).

### **III. Terraform Infrastructure Setup**

Create a terraform directory in the project root to hold your infrastructure-as-code files.

#### **1\. terraform/versions.tf**

This file specifies the required Terraform version and the necessary providers. Your configuration should require the hashicorp/google and hashicorp/random providers.

#### **2\. terraform/variables.tf**

Define the input variables for your Terraform configuration to make it reusable. At a minimum, include:

* gcp\_project\_id: The ID of the GCP project for deployment.
* gcp\_region: The GCP region for the resources (e.g., us-central1).
* service\_name: A base name to use for all created resources (e.g., dispinmap-bot).

#### **3\. terraform/main.tf**

This file will contain the definitions for all the GCP resources. The key resources to create are:

1. **Enabled APIs:** Programmatically enable the necessary APIs, such as Cloud Run, Cloud SQL, Secret Manager, and Artifact Registry.
2. **Artifact Registry:** A Docker repository to store your container images.
3. **Networking:** A VPC Network and a VPC Access Connector to allow Cloud Run to communicate with the Cloud SQL instance over a private IP address.
4. **Cloud SQL:** A PostgreSQL database instance, including the database itself and a dedicated user with a randomly generated password.
5. **Secret Manager:** A secret to hold the Discord bot token. Note that Terraform should only create the *container* for the secret, not the secret value itself.
6. **Service Account & IAM:** A dedicated Identity and Access Management (IAM) service account for the Cloud Run service. This account needs to be granted the "Cloud SQL Client" role to connect to the database and the "Secret Manager Secret Accessor" role to read the token secret.
7. **Cloud Run Service:** The main service that runs the bot. Key configurations include:
   * Setting min\_instance\_count to 1 to ensure the bot runs continuously.
   * Attaching the dedicated service account created in the previous step.
   * Pointing to the container image in Artifact Registry.
   * Passing the database and secret information as environment variables (e.g., DB\_TYPE, DB\_INSTANCE\_CONNECTION\_NAME, DB\_USER, DB\_PASS, DB\_NAME, DISCORD\_TOKEN\_SECRET\_NAME).
   * Connecting it to the VPC connector for private database access.

#### **4\. terraform/outputs.tf**

Expose important information from your infrastructure deployment as outputs. This makes it easy to find key values after running Terraform.

* cloud\_run\_service\_url: The public URL of the deployed Cloud Run service.
* discord\_token\_secret\_id: The ID of the Secret Manager secret, so you know where to add the token value manually.
* artifact\_registry\_repository\_url: The full URL of the container repository, which is needed for pushing the bot's image.

### **IV. Documentation and Local Development Updates**

#### **1\. Update README.md**

Your project's README should be updated with clear instructions for both local development and GCP deployment.

* **Local Development:** Explain how to set up the .env file with the DISCORD\_BOT\_TOKEN.
* **GCP Deployment:**
  1. List the prerequisites: gcloud CLI, terraform, and docker (or a compatible tool like Podman).
  2. Provide the necessary authentication commands.
  3. Show the commands to build the container image and push it to the Artifact Registry repository created by Terraform.
  4. List the Terraform commands: terraform init, terraform plan, and terraform apply.
  5. **Crucially, add a prominent note** instructing the user that after a successful terraform apply, they must manually navigate to Secret Manager in the GCP Console and add the Discord token as a new version to the secret that was created.

#### **2\. Verify .env.example**

Ensure you have an example environment file (.env.example) in your repository that clearly shows the DISCORD\_BOT\_TOKEN variable that users need to define for local development.
