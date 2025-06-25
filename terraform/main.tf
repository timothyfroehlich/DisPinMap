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
    "servicenetworking.googleapis.com",
    "storage.googleapis.com"
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

# Cloud Storage bucket for SQLite database backups (Litestream)
resource "google_storage_bucket" "sqlite_backups" {
  name     = "${var.service_name}-sqlite-backups"
  location = var.gcp_region

  # Enable versioning for backup history
  versioning {
    enabled = true
  }

  # Lifecycle management to control storage costs
  lifecycle_rule {
    condition {
      age = 30
    }
    action {
      type = "Delete"
    }
  }

  # Lifecycle rule to move older versions to cheaper storage
  lifecycle_rule {
    condition {
      age                   = 7
      with_state           = "ARCHIVED"
    }
    action {
      type = "Delete"
    }
  }

  # Uniform bucket-level access
  uniform_bucket_level_access = true

  depends_on = [google_project_service.required_apis]
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

# IAM binding for Cloud SQL Client role (retained for possible future use, but not required for SQLite)
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

# IAM binding for Cloud Storage access (Litestream backups)
resource "google_storage_bucket_iam_member" "litestream_storage_admin" {
  bucket = google_storage_bucket.sqlite_backups.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.cloud_run_sa.email}"
}

# Cloud Run Service
resource "google_cloud_run_v2_service" "bot_service" {
  name     = var.service_name
  location = var.gcp_region

  template {
    scaling {
      # COST OPTIMIZATION: Minimal scaling for Discord bot
      # Discord bots require persistent WebSocket connections, so min_instance_count = 1
      min_instance_count = 1
      max_instance_count = 3
    }

    service_account = google_service_account.cloud_run_sa.email

    containers {
      image = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker_repo.repository_id}/${var.service_name}:latest"

      ports {
        container_port = 8080
      }

      # SQLITE MODE - ACTIVE FOR COST OPTIMIZATION
      env {
        name  = "DB_TYPE"
        value = "sqlite"
      }

      env {
        name  = "DATABASE_PATH"
        value = "/tmp/pinball_bot.db"
      }

      # Litestream backup configuration
      env {
        name  = "LITESTREAM_BUCKET"
        value = google_storage_bucket.sqlite_backups.name
      }

      env {
        name  = "LITESTREAM_PATH"
        value = "/tmp/pinball_bot.db"
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
          # Cloud Run minimum requirements for always-allocated instances
          memory = "512Mi"
          cpu    = "1000m"
        }
      }
    }
  }

  depends_on = [
    google_project_service.required_apis
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
