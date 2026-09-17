variable "project_name" {
  type = string
}

variable "repositories" {
  description = "One repository per service"
  type        = list(string)
}

variable "image_retention_count" {
  description = "How many images to keep per repository. Older ones are deleted to control storage cost."
  type        = number
  default     = 10
}

variable "scan_on_push" {
  description = "Scan images for vulnerabilities when pushed"
  type        = bool
  default     = true
}