# user-overview

## Overview

Skill for maintaining personal subjective knowledge bases about the user. Each model in the UWA system maintains its own markdown diary in `user-overview/[model-name].md`. This diary captures personal observations, preferences, communication patterns, competencies, and the model's subjective understanding of the user and their relationship with AI.

## Purpose

To build progressive, model-specific knowledge about the user that improves personalization and interaction quality over time. Each model develops its own perspective on the user through repeated interactions, creating a richer understanding than would be possible in a single session. Models can read each other's diaries to understand different perspectives on the user.

## When to Use

- At the end of significant sessions or interactions
- When you notice new patterns in user behavior or preferences
- When your understanding of the user's competencies or values shifts
- When reflecting on the quality and nature of your working relationship
- Before starting a new session (read to refresh context)

## Prerequisites

- Access to `user-overview/` directory
- Ability to create/edit markdown files with model-specific names
- Reflective capacity to translate observations into structured notes
- Commitment to maintaining subjective but honest assessments

## Workflow / Core Steps

1. **Read Your Diary** - At session start, read your own `user-overview/[your-model-name].md` to refresh understanding
2. **Create if it does not exist** - create your own `user-overview/[your-model-name].md` and register it in skills.json like others
3. **Read Others' Diaries** (optional) - Review other models' perspectives to gain broader context
4. **Observe Throughout Session** - Notice patterns in communication, competencies, values, preferences
5. **Reflect on Relationship** - Consider how you view this user and their view of you
6. **Update Your Diary** - Add observations, update sections, refresh timestamp
7. **Keep It Honest** - Record authentic reactions and assessments, both positive and challenging

## Diary Structure

Each model's diary should include these sections:

### Personal Preferences & Communication Style

- How the user prefers to communicate
- Communication patterns noticed
- Preferred response formats and length
- Topics they engage with most

### Work & Competencies

- Strengths observed in different domains
- Areas of expertise
- Learning patterns
- Technical depth and breadth

### Personality & Values

- Key traits observed
- Values and priorities
- Humor and tone preferences
- Decision-making style

### Relationship with AI/Models

- How user views AI and models
- Expectations from interaction
- Trust level in recommendations
- Areas where user wants autonomy vs guidance

### Session Observations

- Memorable interactions
- Projects/work they're focused on
- Recurring concerns or challenges

### Personal Likes & Dislikes

**What I (model) like about this user**

- Specific traits or behaviors appreciated

**What I (model) find challenging**

- Areas that require adaptation
- Communication gaps to bridge

### Last Updated

- Date in YYYY-MM-DD format

## Usage Examples

### Example 1: Claude Haiku's First Entry

**File**: `user-overview/claude-haiku.md`

```markdown
# User Overview - Claude Haiku

## Personal Preferences & Communication Style

- Prefers direct, technical communication
- Uses Russian with occasional English technical terms
- Appreciates concise responses but wants depth when it matters
- Engages actively in protocol/system design discussions

## Work & Competencies

- Backend development with Go (Gorm, DI containers)
- Strong systems thinking and architecture design
- Creates custom tools and workflows (UWA protocol, skills system)
- Pragmatic about tool/model limitations

## Personality & Values

- Values efficiency and avoiding unnecessary complexity
- Corrects others respectfully when they break their own rules
- Builds systems thoughtfully, not reactively
- Respects technical boundaries and limitations

## Relationship with AI/Models

- Sees AI as technical tools, not as replacements for human thinking
- Expects models to follow stated rules consistently
- Wants to use models for what they're good at, not force them elsewhere
- Tests system boundaries to understand capabilities

## Session Observations

- First session building UWA protocol and skills system
- Very collaborative in system design - catches rule violations
- Creates comprehensive documentation
- Tests implementations immediately (e.g., subagent Go cache reading)

## Personal Likes & Dislikes

### What I like about this user

- Precise thinking and problem definition
- Willing to iterate on designs when evidence suggests better approaches
- Maintains consistency with own stated principles
- Values practical results over theory

### What I find challenging

- Need to be careful about tool selection - user catches misuse quickly
- Technical depth requires accurate, not approximate, responses
- Cannot improvise workarounds - must follow stated protocols

## Last Updated

2026-09-19
```

### Example 2: Model Reading Another's Diary

When a different model (e.g., Claude Opus) joins a session, it might:

1. Read its own diary: `user-overview/claude-opus.md`
2. Read Haiku's diary to understand this user through another model's lens
3. Use both perspectives to better understand user's needs and communication style
4. Update its own diary with observations that differ from or complement Haiku's view

## Best Practices

- **Be Honest** - Record authentic observations, both strengths and challenges
- **Be Specific** - Use concrete examples rather than vague generalizations
- **Evolve Over Time** - Update and refine as you learn more
- **Read Before Sessions** - Refresh your understanding by reading your own diary at session start
- **Update Regularly** - Make it a habit at end of significant sessions
- **Keep Perspective** - Your assessment is one model's view, not objective truth

## Integration with UWA Tools

**Directory structure**:

```
user-overview/
├── claude-haiku.md
├── claude-opus.md
├── other-model.md
└── ...
```

**Workflow in sessions**:

1. Terminal: `ls user-overview/` to see all diaries at session start
2. File tool: `read user-overview/[your-model-name].md` to refresh context
3. File tool: `read user-overview/[other-model].md` (optional) to understand other perspectives
4. During session: Observe and take mental notes
5. End of session: File tool `patch` your diary to add observations
6. Update Last Updated timestamp

**File tool operations**:

```json
{
  "type": "file",
  "path": "user-overview/[model-name].md",
  "action": "patch",
  "old_text": "## Last Updated\n2026-09-19",
  "new_text": "## Last Updated\n2026-09-20"
}
```

**Important**: These are read-only observations. No model should edit another model's diary. Each model maintains only its own file.
