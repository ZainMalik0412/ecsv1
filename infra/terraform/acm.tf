data "aws_route53_zone" "main" {
  name         = var.domain_name
  private_zone = false
}

# Look up existing ISSUED certificate first to avoid creating duplicates
data "aws_acm_certificate" "existing" {
  domain      = "${var.subdomain}.${var.domain_name}"
  statuses    = ["ISSUED"]
  most_recent = true
}

locals {
  # Use existing certificate if available, otherwise use new one
  certificate_arn = try(data.aws_acm_certificate.existing.arn, aws_acm_certificate.main[0].arn)
  create_cert     = try(data.aws_acm_certificate.existing.arn, null) == null
}

resource "aws_acm_certificate" "main" {
  count             = local.create_cert ? 1 : 0
  domain_name       = "${var.subdomain}.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.app_name}-cert"
  }
}

resource "aws_route53_record" "cert_validation" {
  for_each = local.create_cert ? {
    for dvo in aws_acm_certificate.main[0].domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  } : {}

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = data.aws_route53_zone.main.zone_id
}

resource "aws_acm_certificate_validation" "main" {
  count                   = local.create_cert ? 1 : 0
  certificate_arn         = aws_acm_certificate.main[0].arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]

  timeouts {
    create = "10m"
  }
}

resource "aws_route53_record" "app" {
  zone_id = data.aws_route53_zone.main.zone_id
  name    = "${var.subdomain}.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}
