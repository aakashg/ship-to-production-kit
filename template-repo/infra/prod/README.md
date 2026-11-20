# infra/prod
Terraform for the prod environment. Stub: add your real modules here.

Expected files: main.tf (providers and backend), network.tf (VPC, subnets), db.tf (database), service.tf (containers or functions), outputs.tf.
Rules: every change is a PR. CODEOWNERS requires the platform team. Run `terraform plan` in CI and paste the plan in the PR. Never apply from a laptop.
