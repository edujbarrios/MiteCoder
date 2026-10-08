# Security policy

## Supported versions

MiteCoder is currently alpha software. Security fixes are applied to the latest release and the
default branch only.

## Reporting a vulnerability

Please do not open a public issue for a vulnerability that could expose files, execute an
unconfigured command, escape the selected workspace, or compromise a host running MiteCoder.
Use GitHub's private vulnerability reporting feature for this repository. Include the affected
version, platform, configuration, reproduction steps, impact, and any suggested mitigation.

If private reporting is unavailable, open a minimal issue asking the maintainer for a private
contact channel without publishing exploit details. You should receive an acknowledgement within
seven days. Disclosure timing will be coordinated after the report has been validated and a fix is
available.

## Trust model

Local model output and repository content are untrusted. MiteCoder confines file tools to the
chosen workspace and limits command execution to test commands in operator-controlled
configuration. Run the agent on repositories and model files you trust, review diffs before
committing, and use operating-system isolation for hostile inputs. MiteCoder does not provide a
general sandbox for arbitrary commands or malicious native model libraries.
