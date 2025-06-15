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
    "compute.googleapis.com",
    "servicenetworking.googleapis.com"
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

# Random password for database user
resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Cloud SQL PostgreSQL instance (public IP only)
resource "google_sql_database_instance" "postgres_instance" {
  name             = "${var.service_name}-db-instance"
  database_version = "POSTGRES_15"
  region           = var.gcp_region

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled = true
      # No private_network or enable_private_path_for_google_cloud_services
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
    google_project_service.required_apis
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

# Secret Manager secret for database password
resource "google_secret_manager_secret" "db_password" {
  secret_id = "${var.service_name}-db-password"

  replication {
    user_managed {
      replicas {
        location = var.gcp_region
      }
    }
  }

  depends_on = [google_project_service.required_apis]
}

# Secret Manager secret version for database password
resource "google_secret_manager_secret_version" "db_password_version" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = random_password.db_password.result
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
        name  = "DB_PASSWORD_SECRET_NAME"
        value = google_secret_manager_secret.db_password.secret_id
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
    google_sql_database_instance.postgres_instance
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
