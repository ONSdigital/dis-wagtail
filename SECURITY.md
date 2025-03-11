# VULNERABILITY DISCLOSURE POLICY

## Scope

This disclosure policy applies only to vulnerabilities in the ONS products and services under the following conditions:

- ‘In scope’ vulnerabilities must be original, previously unreported, and not already discovered by internal procedures.
- Volumetric vulnerabilities are not in scope - meaning that simply overwhelming a service with a high volume of
  requests is not in scope.
- Reports of non-exploitable vulnerabilities, or reports indicating that our services do not fully align with 'best
  practice', for example missing security headers, are not in scope.
- TLS configuration weaknesses, for example 'weak'cipher suite support or the presence of TLS1.0 support, are not in
  scope.
- The policy applies to everyone, including for example the ONSstaff, third party suppliers and general users of the ONS
  publicservices.

## Reporting

If you have discovered something you believe to be an in-scope security vulnerability, first you should check the above
details for more information about scope, then submit a report
on [this page](https://hackerone.com/52fa7bc0-5356-4c86-9f79-eeb03e1d55cc/embedded_submissions/new). In your submission,
include details of:

- The website or page where the vulnerability can be observed.
- A brief description of the type of vulnerability, for example an 'XSS vulnerability'.

Your report should provide a benign, non-destructive, proof of exploitation. This helps to ensure that the report can be
triaged quickly and accurately. It also reduces the likelihood of duplicate reports, or malicious exploitation of some
vulnerabilities, such as sub-domain takeovers.

## What to expect

After you have submitted your report, we will respond to your report within 5 working days and aim to triage your report
within 10 working days. We’ll also keep you informed about our progress throughout the process via HackerOne if you have
registered for an account.

Priority for bug fixes or mitigations are assessed by looking at the impact severity and exploit complexity.
Vulnerability reports might take some time to triage or address. You are welcome to enquire onthe status of the process
but should avoid doing so more than once every 14 days. The reason is to allow our teams to focus on the reports as much
as possible.

When the reported vulnerability is resolved, or remediation work is scheduled, the Vulnerability Disclosure Team will
notify you, and invite you to confirm that the solution covers the vulnerability adequately.

## Legalities

This policy is designed to be compatible with common vulnerability disclosure good practice. It does not give you
permission to act in any manner that is inconsistent with the law, or which might cause the ONS to be in breach of any
of its legal obligations, including but not limited to:

- The Computer Misuse Act (1990)
- The General Data Protection Regulation 2016/679 (GDPR) and the Data Protection Act 2018
- The Copyright, Designs and Patents Act (1988)
- The Official Secrets Act (1989)

The ONS affirms that it will not seek prosecution of any security researcher who reports any security vulnerability on a
ONS service or system, where the researcher has acted in good faith and in accordance with this disclosure policy.

## Guidance

You must NOT:

- Access unnecessary amounts of data. For example, 2 or 3 records is enough to demonstrate most vulnerabilities, such
  asan enumeration or direct object reference vulnerability.
- Use high-intensity invasive or destructive technical security scanning tools to find vulnerabilities.
- Violate the privacy of the ONS users, staff, contractors, services or systems. For example, by sharing, redistributing
  and/or not properly securing data retrieved from our systems or services.
- Communicate any vulnerabilities or associated details using methods not described in this policy.
- Modify data in the ONS systems or services.
- Disrupt the ONS services or systems.
- Social engineer, 'phish' or physically attack ONS staff or infrastructure.
- Disclose any vulnerabilities in the ONS systems or services to 3rd parties or the public, prior to the ONS confirming
  that those vulnerabilities have been mitigated or rectified. However, this is not intended to stop you notifying a
  vulnerability to 3rd parties for whom the vulnerability is directly relevant. An example would be where the
  vulnerability being reported is in a 3rd party software library or framework. Details of the specific vulnerability as
  it applies to the ONS must not be referenced in such reports.
