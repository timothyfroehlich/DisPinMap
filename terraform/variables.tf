variable "gcp_project_id" {
  description = "The ID of the GCP project for deployment"
  type        = string
}

variable "gcp_region" {
  description = "The GCP region for the resources"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Base name to use for all created resources"
  type        = string
  default     = "dispinmap-bot"
}