# Migration Test Workflow

## Steps
1. Verify all rules load correctly
2. Test skill detection patterns
3. Validate workflow execution
4. Check Memory Bank functionality

## Validation Commands
```bash
# Test skills integration
grep -c "SKILL.md" .sixthrules/02-skills-integration.md

# Test workflow references
find .sixthworkflows -name "*.md" -exec grep -l "\.sixth" {} \;

# Test memory bank
ls -la memory-bank/
```

## Structure Validation
```bash
# Verify complete structure
echo "=== Sixth Structure ==="
tree .sixthrules .sixthworkflows .sixthskills 2>/dev/null || find .sixth* -type f | sort

# Count components
echo "Rules: $(ls .sixthrules/*.md | wc -l)"
echo "Workflows: $(ls .sixthworkflows/*.md | wc -l)"
echo "Skills: $(find .sixthskills -name SKILL.md | wc -l)"
```
