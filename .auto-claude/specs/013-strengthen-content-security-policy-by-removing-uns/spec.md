# Strengthen Content Security Policy by Removing unsafe-inline for Styles

## Overview

The CSP configuration in backend/config/settings/base.py (line 195) includes 'unsafe-inline' for CSP_STYLE_SRC: `CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")`. While noted as needed for admin styles, this weakens XSS protections across the entire application and enables CSS-based data exfiltration attacks.

## Rationale

Content Security Policy is a critical defense-in-depth measure against XSS attacks. The 'unsafe-inline' directive for styles can be exploited by attackers to exfiltrate data using CSS-based attacks (e.g., attribute selectors to read input values character by character). Modern applications can use CSP nonces or hash-based allowlisting instead.

---
*This spec was created from ideation and is pending detailed specification.*
