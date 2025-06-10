# Configure the Google Cloud Provider
provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "sql-component.googleapis.com",
    "sqladmin.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "vpcaccess.googleapis.com",
    "compute.googleapis.com"
  ])
  
  project = var.gcp_project_id
  service = each.value
  
  disable_dependent_services = false
}

# Artifact Registry for container images
resource "google_artifact_registry_repository" "docker_repo" {
  location      = var.gcp_region
  repository_id = "${var.service_name}-repo"
  description   = "Docker repository for ${var.service_name}"
  format        = "DOCKER"
  
  depends_on = [google_project_service.required_apis]
}

# VPC Network for private database access
resource "google_compute_network" "vpc_network" {
  name                    = "${var.service_name}-vpc"
  auto_create_subnetworks = false
  
  depends_on = [google_project_service.required_apis]
}

# Subnet for VPC connector
resource "google_compute_subnetwork" "vpc_subnet" {
  name          = "${var.service_name}-subnet"
  ip_cidr_range = "10.0.0.0/28"
  region        = var.gcp_region
  network       = google_compute_network.vpc_network.id
}

# VPC Access Connector for Cloud Run to Cloud SQL communication
resource "google_vpc_access_connector" "vpc_connector" {
  name          = "${var.service_name}-connector"
  region        = var.gcp_region
  network       = google_compute_network.vpc_network.name
  ip_cidr_range = "10.8.0.0/28"
  
  depends_on = [google_project_service.required_apis]
}

# Random password for database user
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Cloud SQL PostgreSQL instance
resource "google_sql_database_instance" "postgres_instance" {
  name             = "${var.service_name}-db-instance"
  database_version = "POSTGRES_15"
  region           = var.gcp_region
  
  settings {
    tier = "db-f1-micro"
    
    ip_configuration {
      ipv4_enabled                                  = false
      private_network                              = google_compute_network.vpc_network.id
      enable_private_path_for_google_cloud_services = true
    }
    
    backup_configuration {
      enabled = true
    }
    
    database_flags {
      name  = "cloudsql.iam_authentication"
      value = "on"
    }
  }
  
  deletion_protection = false
  
  depends_on = [
    google_project_service.required_apis,
    google_compute_network.vpc_network
  ]
}

# Database
resource "google_sql_database" "database" {
  name     = var.service_name
  instance = google_sql_database_instance.postgres_instance.name
}

# Database user
resource "google_sql_user" "db_user" {
  name     = "${var.service_name}-user"
  instance = google_sql_database_instance.postgres_instance.name
  password = random_password.db_password.result
}

# Secret Manager secret for Discord token (empty - must be populated manually)
resource "google_secret_manager_secret" "discord_token" {
  secret_id = "${var.service_name}-discord-token"
  
  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }
  
  depends_on = [google_project_service.required_apis]
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.service_name}-sa"
  display_name = "Service Account for ${var.service_name} Cloud Run"
}

# IAM binding for Cloud SQL Client role
resource "google_project_iam_member" "cloud_sql_client" {
  project = var.gcp_project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# IAM binding for Secret Manager Secret Accessor role
resource "google_project_iam_member" "secret_accessor" {
  project = var.gcp_project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "bot_service" {
  name     = var.service_name
  location = var.gcp_region
  
  template {
    scaling {
      min_instance_count = 1
      max_instance_count = 1
    }
    
    service_account = google_service_account.cloud_run_sa.email
    
    vpc_access {
      connector = google_vpc_access_connector.vpc_connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    
    containers {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/${var.service_name}:latest"
      
      ports {
        container_port = 8080
      }
      
      env {
        name  = "DB_TYPE"
        value = "postgres"
      }
      
      env {
        name  = "DB_INSTANCE_CONNECTION_NAME"
        value = google_sql_database_instance.postgres_instance.connection_name
      }
      
      env {
        name  = "DB_USER"
        value = google_sql_user.db_user.name
      }
      
      env {
        name  = "DB_PASS"
        value = random_password.db_password.result
      }
      
      env {
        name  = "DB_NAME"
        value = google_sql_database.database.name
      }
      
      env {
        name  = "DISCORD_TOKEN_SECRET_NAME"
        value = google_secret_manager_secret.discord_token.secret_id
      }
      
      env {
        name  = "GOOGLE_CLOUD_PROJECT"
        value = var.gcp_project_id
      }
      
      resources {
        limits = {
          memory = "512Mi"
          cpu    = "1000m"
        }
      }
    }
  }
  
  depends_on = [
    google_project_service.required_apis,
    google_sql_database_instance.postgres_instance,
    google_vpc_access_connector.vpc_connector
  ]
}

# Allow unauthenticated requests to Cloud Run (for health checks)
resource "google_cloud_run_service_iam_member" "public_access" {
  location = google_cloud_run_v2_service.bot_service.location
  project  = google_cloud_run_v2_service.bot_service.project
  service  = google_cloud_run_v2_service.bot_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}