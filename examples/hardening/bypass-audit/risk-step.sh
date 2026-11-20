# Include the OLD path of renames (previous_filename), or moving a file out of auth/ looks harmless.
# Fail closed: an API error, an empty list, or a huge PR (the API stops listing at 3000 files) counts as high risk.
if ! files=$(gh api "repos/$REPO/pulls/$PR/files" --paginate --jq '.[] | .filename, (.previous_filename // empty)'); then
  echo "high=true" >> "$GITHUB_OUTPUT"; exit 0
fi
echo "$files"
if [ -z "$files" ] || [ "$(echo "$files" | wc -l)" -ge 3000 ]; then
  echo "high=true" >> "$GITHUB_OUTPUT"; exit 0
fi
# (^|/) so a top-level auth/ folder matches too, not only app/auth/. Case-insensitive. Keep in sync with CODEOWNERS.
HIGH='(^|/)(infra|terraform|migrations|migration|auth|authn|authz|billing|payments|secrets|\.github|\.claude)/|^(\.coderabbit\.yaml|claude\.md|codeowners|docs/codeowners)$|(^|/)(\.env[^/]*|[^/]*\.tf|[^/]*\.tfvars|[^/]*\.pem|[^/]*\.key)$'
if echo "$files" | grep -E -i -q "$HIGH"; then
  echo "high=true" >> "$GITHUB_OUTPUT"
else
  echo "high=false" >> "$GITHUB_OUTPUT"
fi
