# A.R.T.E.M.I.S.

Sprint backlog, eight sprints, one per build-sequence stage in Architecture Revision 2 (Section 13). Stage numbers are unchanged; stage N is delivered in sprint N plus one.

Numbering continues from the work already delivered: Sprint 0 covered the proposal and data collection, Sprint 1 the literature review and Architecture Revision 2. Implementation therefore begins at Sprint 2, and the eight build-sequence stages run from Sprint 2 to Sprint 9.

Dates below are placeholders on a contiguous two-week cadence. Replace them with the real FYP milestone dates. Sprints 2 to 5 are Semester 1, sprints 6 to 9 are Semester 2.

Points are Fibonacci, 1 to 13. The last story in each sprint is that stage's gate from Section 13, because a stage is not done until its gate passes.

## Sprint 2: Workspace Foundation
Goal: The boundary exists and is provably unescapable, with no model involved
Start: 2026-09-28
End: 2026-10-11

### User can opt a folder in as a workspace
Type: Story
Priority: Critical
Points: 8

### System cannot resolve any path outside a granted workspace
Type: Story
Priority: Critical
Points: 13

### User can see every file the system has indexed, and delete any of it
Type: Story
Priority: Critical
Points: 13

### Stage gate: traversal and symlink escapes are refused and logged
Type: Story
Priority: Critical
Points: 3

## Sprint 3: Trust Machinery
Goal: Every gate works and is testable before any model exists
Start: 2026-10-12
End: 2026-10-25

### System classifies every proposed action into exactly one risk tier
Type: Story
Priority: Critical
Points: 13

### System has no code path to a destructive operation
Type: Story
Priority: Critical
Points: 5

### User can preview and approve or reject a pending action
Type: Story
Priority: Critical
Points: 13

### User can undo an approved plan as a single unit
Type: Story
Priority: Critical
Points: 13

### Auditor can read an append-only record of every proposal and action
Type: Story
Priority: High
Points: 5

### Stage gate: gates hold against placeholder tools
Type: Story
Priority: Critical
Points: 5

## Sprint 4: AI Gateway
Goal: The highest-risk stage, validated against gates that already work
Start: 2026-10-26
End: 2026-11-08

### System routes a request to a local model by default, with bounded failover
Type: Story
Priority: Critical
Points: 13

### Workspace data never reaches a model tier the workspace has disabled
Type: Story
Priority: Critical
Points: 8

### Retrieved context never includes content outside the active grant
Type: Story
Priority: Critical
Points: 13

### System produces an inspectable plan without executing it
Type: Story
Priority: Critical
Points: 13

### Only the dispatcher may execute, and only with a policy verdict
Type: Story
Priority: Critical
Points: 8

### Stage gate: the gateway cannot act around the gates
Type: Story
Priority: Critical
Points: 5

## Sprint 5: Core File Features
Goal: First real capabilities, exercising the read and reversible tiers end to end
Start: 2026-11-09
End: 2026-11-22

### User can pick up where they left off
Type: Story
Priority: High
Points: 8

### User can tidy a folder after previewing every move
Type: Story
Priority: High
Points: 13

### User is offered automation only after a pattern repeats three times
Type: Story
Priority: Medium
Points: 8

### Capability services reach the filesystem only through the broker
Type: Story
Priority: Critical
Points: 8

### Stage gate: three features run end to end through real gates
Type: Story
Priority: Critical
Points: 3

## Sprint 6: Document and Code Understanding
Goal: Add the vector index once the boundary is proven
Start: 2026-11-23
End: 2026-12-06

### System indexes a workspace incrementally without blocking the interactive path
Type: Story
Priority: High
Points: 13

### User can synthesise notes with every claim traceable to a source
Type: Story
Priority: High
Points: 13

### User can ask about code and receive a diff, never an edit
Type: Story
Priority: High
Points: 13

### Retrieval stays fast as a workspace grows
Type: Story
Priority: Medium
Points: 8

### Stage gate: an unsupported claim renders as unsupported
Type: Story
Priority: Critical
Points: 3

## Sprint 7: Outward Actions
Goal: The first outward-tier actions, only after the gates are demonstrated
Start: 2026-12-07
End: 2026-12-20

### User can search the web on demand and never in the background
Type: Story
Priority: Medium
Points: 8

### User can send mail only after approving the draft
Type: Story
Priority: Medium
Points: 13

### User can generate a draft document without losing an existing one
Type: Story
Priority: Medium
Points: 8

### User can see exactly what left the machine and when
Type: Story
Priority: High
Points: 5

### Stage gate: no outward action escapes its gate
Type: Story
Priority: Critical
Points: 3

## Sprint 8: Speech Input and Output
Goal: Prove voice parity is structural by writing no new gates
Start: 2026-12-21
End: 2027-01-03

### User can speak a request and reach the same gates as typing
Type: Story
Priority: Medium
Points: 13

### User is never recorded unless they armed the session
Type: Story
Priority: Critical
Points: 8

### User can hear a spoken result for a voice turn
Type: Story
Priority: Low
Points: 5

### Stage gate: speech required no new approval gates
Type: Story
Priority: Critical
Points: 3

## Sprint 9: Remote Access Plane
Goal: Optional by construction, removing it changes nothing locally
Start: 2027-01-04
End: 2027-01-17

### User can pair a remote device with their host machine
Type: Story
Priority: Low
Points: 13

### Relayed traffic is unreadable to the edge
Type: Story
Priority: Critical
Points: 13

### Remote access never grants more than local access
Type: Story
Priority: Critical
Points: 8

### Stage gate: deleting the remote plane changes nothing locally
Type: Story
Priority: Critical
Points: 3
