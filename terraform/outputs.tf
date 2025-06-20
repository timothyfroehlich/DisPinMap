output "cloud_run_service_url" {
  description = "The public URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.bot_service.uri
}

output "discord_token_secret_id" {
  description = "The ID of the Secret Manager secret for manual Discord token addition"
  value       = google_secret_manager_secret.discord_token.secret_id
}

output "artifact_registry_repository_url" {
  description = "The full URL of the container repository for pushing images"
  value       = "${var.gcp_region}-docker.pkg.dev/${var.gcp_project_id}/${google_artifact_registry_repository.docker_repo.repository_id}"
}

output "database_connection_name" {
  description = "Cloud SQL instance connection name"
  value       = google_sql_database_instance.postgres_instance.connection_name
}

output "service_account_email" {
  description = "Email of the service account used by Cloud Run"
  value       = google_service_account.cloud_run_sa.email
}
