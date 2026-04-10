# ============================================================================
# ACM Module
# Manages SSL/TLS certificates for HTTPS and DNS validation via Route 53
# Also creates the Route 53 A record pointing the subdomain to the ALB
# ============================================================================

# Look up the existing Route 53 hosted zone for the base domain
# This zone must already exist (created outside of Terraform)
data "aws_route53_zone" "main" {
  # The base domain name to look up (e.g. "zainecs.com")
  name = var.domain_name
  # Only search public hosted zones (not VPC-private zones)
  private_zone = false
}

# Local values for certificate ARN reference
locals {
  # Reference the certificate ARN from the always-created resource
  certificate_arn = aws_acm_certificate.main.arn
}

# Create an ACM certificate for the application subdomain
# The destroy pipeline cleans up orphaned certificates, so we always create fresh
resource "aws_acm_certificate" "main" {
  # The domain name this certificate will secure
  domain_name = "${var.subdomain}.${var.domain_name}"
  # Use DNS validation (automated via Route 53) instead of email validation
  validation_method = "DNS"

  # Create the new certificate before destroying the old one during replacement
  lifecycle {
    create_before_destroy = true
  }

  # Tags for resource identification
  tags = {
    Name = "${var.app_name}-cert"
  }
}

# Create DNS validation records in Route 53 to prove domain ownership
# ACM requires these CNAME records to validate and issue the certificate
resource "aws_route53_record" "cert_validation" {
  # Iterate over the domain validation options provided by ACM
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  # Allow overwriting existing records (safe for validation CNAMEs)
  allow_overwrite = true
  # The DNS record name provided by ACM for validation
  name = each.value.name
  # The DNS record value provided by ACM for validation
  records = [each.value.record]
  # Short TTL so changes propagate quickly
  ttl = 60
  # Record type (always CNAME for ACM DNS validation)
  type = each.value.type
  # Place the record in our hosted zone
  zone_id = data.aws_route53_zone.main.zone_id
}

# Wait for the ACM certificate to be validated and issued
# This blocks until AWS confirms the DNS validation records are correct
resource "aws_acm_certificate_validation" "main" {
  # The certificate to validate
  certificate_arn = aws_acm_certificate.main.arn
  # The FQDNs of the validation records (proves they were created)
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]

  # Allow up to 10 minutes for DNS propagation and certificate issuance
  timeouts {
    create = "10m"
  }
}

# Create a Route 53 A record that points the application subdomain to the ALB
# This is what makes https://tm.zainecs.com resolve to the load balancer
resource "aws_route53_record" "app" {
  # Place in the same hosted zone as the domain
  zone_id = data.aws_route53_zone.main.zone_id
  # Full subdomain name (e.g. "tm.zainecs.com")
  name = "${var.subdomain}.${var.domain_name}"
  # A record type (IPv4 address)
  type = "A"

  # Use an alias record instead of a static IP - this is an AWS best practice
  # for pointing to ALBs, CloudFront, etc. (no TTL needed, no charge for queries)
  alias {
    # The ALB's DNS name (e.g. "attendancems-alb-123456.eu-west-2.elb.amazonaws.com")
    name = var.alb_dns_name
    # The ALB's Route 53 hosted zone ID (AWS-managed, specific to the region)
    zone_id = var.alb_zone_id
    # Enable health checking - Route 53 will only route to healthy ALBs
    evaluate_target_health = true
  }
}
