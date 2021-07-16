# insight-analytics

An scheduled task that automatically pulls metrics for the last published newsletter in MailChimp. It uses the Python SDKs for Mailchimp and Google Sheets to export and import the data. And it uses Terraform and AWS ECS Fargate to configure the script to run on a weekly schedule automatically.
