# skill-creator

## Overview
Meta-skill for creating, refining, and validating new skills for the UWA system. Enables systematic development of reusable skill modules that extend agent capabilities.

## Purpose
To provide a structured process for identifying skill needs, authoring skill documentation, integrating skills into skills.json, and ensuring quality and consistency across the skills library. This meta-skill is used when you recognize a pattern or need for a new reusable capability.

## When to Use
- You recognize a repeatable task pattern that multiple skills or workflows could benefit from
- A user requests a specific capability that doesn't exist as a skill yet
- Refactoring existing agent knowledge into a reusable, documented skill
- Improving or iterating on an existing skill based on usage
- Creating skill variations for different contexts or languages
- Validating that a new skill integrates properly with agent workflow

## Prerequisites
- Understanding of the UWA Tools protocol and available actions (terminal, file tools)
- Familiarity with the skill structure template (8 sections)
- Access to skills.json and skills/ directory
- Basic understanding of what makes a skill reusable vs task-specific

## Workflow / Core Steps
1. **Identify the Need** - Recognize pattern/gap and define skill scope
2. **Plan Skill Structure** - Outline Overview, Purpose, When to Use sections
3. **Author Documentation** - Write complete skill.md in skills/ directory
4. **Update skills.json** - Add skill entry with name, path, description, triggers
5. **Test and Validate** - Verify skill triggers work and integration is correct
6. **Iterate** - Refine based on actual usage patterns

## Usage Examples

### Example 1: Creating a New File Analysis Skill
User needs: "I want a skill for analyzing Go project structure and dependencies"
- Identify: Pattern in scanning codebases
- Create: skill-go-analyzer.md with workflow for examining Go files
- Register: Add to skills.json with triggers like "analyze go project", "go dependencies"
- Validate: Test that it triggers appropriately and produces useful output

### Example 2: Refactoring Existing Knowledge into Skill
Existing: You've used a specific pattern multiple times (e.g., "create database migrations")
- Capture: Document the workflow you've been doing
- Formalize: Create skill-db-migration.md with steps and best practices
- Integrate: Add to skills.json
- Benefit: Future occurrences automatically trigger this documented approach

## Best Practices
- **Trigger Words are Key** - Use 4-6 short-triggers that naturally appear in user requests
- **Avoid Overlap** - Check existing skills before creating new one; consider extending instead
- **Be Specific About Scope** - "When to Use" should be clear boundaries, not everything
- **Include Real Examples** - Usage Examples should be concrete scenarios from actual work
- **Document UWA Integration** - Always explain terminal/file tool usage specific to this skill
- **Keep it Lean** - If a skill section grows too much, consider splitting into sub-skills
- **Test Triggers** - Mentally simulate: would I recognize when to use this skill?

## Integration with UWA Tools
When creating a skill-creator workflow:
1. Use `file` tool with `read` action to examine existing skills for patterns
2. Use `file` tool with `patch` or line-mode to update skills.json
3. Use `terminal` tool to validate JSON syntax: `jq . skills.json`
4. Use `file` tool with `read` to verify new skill.md is properly formatted
5. Consider creating a skill-validation terminal command if multiple skills exist

Typical UWA sequence:
```
1. Read existing skill for structure reference (file read)
2. Create new skill.md in skills/ directory (file patch with new content)
3. Update skills.json with new entry (file patch)
4. Validate JSON is valid (terminal jq)
5. Verify skill works in context (future reference)
```