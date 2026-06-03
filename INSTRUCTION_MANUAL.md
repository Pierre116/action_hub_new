# ActionHub — Instruction Manual

## 1. Overview

ActionHub is a web-based action-tracking platform that replaces Excel logbooks with a unified system for managing actions, meetings, decisions, and dashboards. It is designed for organizations with multiple teams and supports bilingual operation (English / Chinese).

### 1.1 Key Features

| Feature | Description |
|---------|-------------|
| **Meeting Series** | Organize recurring meetings with default participants, access control, and create individual occurrences with agendas, actions, decisions, and memos |
| **Action Management** | Create, assign, and track actions with status workflows, deadlines, priorities, Lead assignment, and progress updates |
| **Decision Tracking** | Record decisions with context, rationale, revision history, and lifecycle management |
| **Dashboards** | Personal, Team, and Global dashboards with KPIs, deadline views, Gantt charts, and workload forecasts |
| **Progress Follow-up** | Update action completion percentage, add comments, and flag blockers — all within meeting context |
| **Notifications** | In-app alerts for assignments, status changes, and approaching deadlines |
| **Access Control** | Private meeting series restrict content visibility to the creator and listed participants only |
| **Export** | Export actions and meeting data to Excel/PDF |
| **Bilingual UI** | Switch between English and Chinese using the language selector in the navigation bar |

### 1.2 User Roles & Access

| Role | Access |
|------|--------|
| **Admin** | Full access — manage users, teams, business themes, view all dashboards, and perform all operations |
| **Team Lead** | Standard access plus Team Dashboard for their own team(s) |
| **Member** | Create and manage actions, participate in meetings, access Personal and Global dashboards |
| **Read Only** | View-only access to actions, meetings, decisions, and dashboards |

### 1.3 Logging In

1. Navigate to the ActionHub URL in your browser.
2. Enter your **Username** and **Password**.
3. Click **Login**.
4. To change your password: use the user menu (top-right) → **Change Password**.

### 1.4 Navigation

The top navigation bar provides access to all major sections:

| Menu Item | Description |
|-----------|-------------|
| **Meeting Series** | List and manage meeting series and their occurrences |
| **Actions** | View, create, and manage actions |
| **Decisions** | View, create, and manage decisions |
| **Dashboard** | Dropdown: Personal Dashboard, Global Dashboard, Team Dashboard |
| **Admin** | *(Admin only)* Manage Users, Teams, and Business Themes |
| **Instructions** | Quick-reference help page |

The right side of the navigation bar contains:
- **Notification bell** — view in-app alerts
- **Theme toggle** — switch between light and dark mode
- **Language selector** — switch between English (EN) and Chinese (ZH)
- **User menu** — profile, change password, logout

---

## 2. Meeting Series

A **Meeting Series** groups related meetings (e.g., weekly team stand-ups, monthly reviews). It defines the topic, default participants, and the business theme.

### 2.1 Viewing Meeting Series

1. Click **Meeting Series** in the navigation bar.
2. The list page shows all series you have access to.

| Column | Description |
|--------|-------------|
| Title | Name of the series |
| Category | Business theme the series belongs to |
| Occurrences | Number of meetings held in this series |
| Access | Shows a **Public** or **Private** badge — private series are restricted to creator and participants |
| Created | Date the series was created |

### 2.2 Creating a New Meeting Series

1. On the Meeting Series list page, click **"New Series"**.
2. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| Title | Yes | Name of the meeting series (e.g., "Weekly Engineering Sync") |
| Category | No | Business theme to associate with this series |
| Description | No | Purpose or scope of the meeting series |

3. Click **Save**. You will be taken to the series detail page.

### 2.3 Managing Series Details

On the series detail page you can:

- **Edit** the title, description, category, and visibility settings.
- **Manage Default Participants**: Add or remove users who should automatically be included in every new occurrence. Each participant can be marked as:
  - **Compulsory** — always required to attend
  - **Optional** — invited but attendance not mandatory

### 2.4 Access Control

Meeting series support **Public** and **Private** visibility:

| Visibility | Behaviour |
|------------|----------|
| **Public** | Any logged-in user can view the series, its occurrences, and all linked content (actions, decisions, memos) |
| **Private** | Only the **series creator** and **listed participants** can access the detail page. Other users see a **lock screen** with the series title and a message to contact the creator |

On the series list page, private series you cannot access display a **lock icon** (🔒) instead of a clickable link.

### 2.5 Creating a Meeting Occurrence

Each occurrence represents one actual meeting within a series.

1. Open the series detail page.
2. In the **Occurrences** section, select a date using the date picker.
3. Click **Create Occurrence**.
4. The new occurrence appears in the occurrences table with columns: Date, Status, Actions count, and Decisions count.

---

## 3. Meeting Occurrences

A meeting occurrence is a single session within a series. It provides a workspace for managing actions, decisions, memos, and follow-up discussions.

### 3.1 Meeting Detail Tabs

When you open a meeting occurrence, you see five tabs:

| Tab | Purpose |
|-----|---------|
| **Overview** | Meeting date, series info, summary, and participants list |
| **Actions** | Actions linked to this meeting — create new or review existing |
| **Decisions** | Decisions made during this meeting |
| **Memos** | Free-text notes and meeting minutes |
| **Follow-up** | Review progress on actions, add comments, view history from previous occurrences |

### 3.2 Adding a Memo

1. Go to the **Memos** tab.
2. Click **"Add Memo"**.
3. Enter the memo **Title** and **Content**.
4. Click **Save**.

---

## 4. Actions

Actions are trackable work items with an owner (Lead), deadline, status, and progress tracking.

### 4.1 Viewing Actions

1. Click **Actions** in the navigation bar.
2. The list page supports filtering:

| Filter | Description |
|--------|-------------|
| Search | Free-text search by title |
| Status | Filter by status (Open, In Progress, On Hold, Done, Cancelled) |
| Category | Filter by business theme |
| Series | Filter by meeting series |
| Lead | Filter by Lead — dropdown shows **your team members** only |
| My Lead | Toggle to show only actions where you are the Lead (on by default) |
| Hide Closed | Toggle to hide Done/Cancelled actions |

3. The actions table displays:

| Column | Description |
|--------|-------------|
| Ref | Unique reference number |
| Title | Action title (clickable to view detail). If the action is linked to a **private meeting series** you are not a member of, the title is **blurred** with a 🔒 indicator |
| Status | Current status with color badge |
| Priority | High / Medium / Low |
| Lead | Assigned lead person |
| Deadline | Target completion date |
| Completion | Progress percentage |
| Category | Associated business theme |

### 4.2 Private Series Actions

Actions linked to a **private meeting series** are subject to access control. If you are **not** the series creator or a participant:

- The action title appears **blurred** with a 🔒 lock indicator.
- You cannot open the action detail page.
- This ensures confidential meeting content remains protected.

### 4.3 Creating an Action

Actions can be created from two places:

#### From the Actions List (standalone action)

1. Click **"New Action"** on the Actions list page.
2. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| Title | Yes | Short description of the action |
| Status | No | Initial status (defaults to Open) |
| Description | No | Detailed description |
| Tags | No | Comma-separated keywords |
| Deadline | No | Target completion date |
| Category | No | Business theme |
| Lead | Auto | Automatically set to the creator |

3. Click **Save**.

#### From a Meeting Occurrence

1. Open a meeting occurrence and go to the **Actions** tab.
2. Click **"New Action"**.
3. The form is the same but with two differences:
   - The meeting context is automatically linked.
   - The **Lead** field is selectable from the meeting participants list (not locked to the creator).

### 4.4 Viewing Action Details

Click any action title to open the detail page. From here you can:

- **Edit** the action via the Edit modal:

| Field | Description |
|-------|-------------|
| Title | Edit the action title |
| Status | Change status (following the allowed transitions — see §6) |
| Priority | Set High / Medium / Low |
| Deadline | Update the target date |
| Description | Modify the detailed description |
| Cancel Reason | *(Required when cancelling)* Explain why the action is cancelled |
| Hold Reason | *(Required when putting on hold)* Explain why the action is paused |

- **View assignments** — see who is assigned and their role
- **View feedback history** — see all progress updates over time
- **View linked decisions** — decisions related to this action

---

## 5. Decisions

Decisions record formal outcomes with context, rationale, and a full revision history.

### 5.1 Viewing Decisions

1. Click **Decisions** in the navigation bar.
2. Filter using:

| Filter | Description |
|--------|-------------|
| Search | Free-text search |
| Status | Published or Expired |
| Series | Filter by meeting series |
| Category | Filter by business theme |
| Creator | Filter by who created the decision |

3. The decisions table displays:

| Column | Description |
|--------|-------------|
| Ref | Unique reference number |
| Title | Decision title |
| Status | Published or Expired |
| Content | Summary of the decision body |
| Category | Business theme |
| Meeting | Linked meeting (if any) |
| Creator | Who created the decision |
| Revisions | Number of revisions |

### 5.2 Creating a Decision

Decisions can be created standalone or from within a meeting:

#### From the Decisions List

1. Click **"Add Decision"** on the Decisions list page.
2. Fill in the form:

| Field | Required | Description |
|-------|----------|-------------|
| Title | Yes | Short summary of the decision |
| Status | No | Published (default) or Expired |
| Content | No | Full text of the decision |
| Context | No | Background information and circumstances |
| Reason | No | Rationale — why this decision was made |
| Tags | No | Comma-separated keywords |
| Category | No | Business theme |

3. Click **Save**.

#### From a Meeting Occurrence

1. Open a meeting occurrence → **Decisions** tab.
2. Click **"Add Decision"**.
3. The meeting is automatically linked to the decision.

### 5.3 Editing a Decision

1. Open the decision detail page.
2. Click **Edit**.
3. Modify any fields and click **Save**.
4. Each edit creates a new **revision** — the full history is preserved and viewable in the **Revision History** section.

### 5.4 Changing Decision Status

- **Published** → **Expired**: When a decision is no longer in effect.
- Status changes are made from the decision detail page.

---

## 6. Action Follow-up & Progress Updates

### 6.1 Updating Progress on an Action

Progress updates (also called "feedback") track how an action advances over time.

1. Open the action detail page.
2. Use the **Progress Update** widget:

| Field | Description |
|-------|-------------|
| Completion % | Drag the slider from 0% to 100% to indicate progress |
| Status | Select the current status from the dropdown |
| Comment | Add a note about what was done or what's next |
| Blockers | Describe any obstacles preventing progress |

3. Click **Update Progress**.
4. The update is recorded with your name and timestamp. All previous updates are visible in the feedback history.

### 6.2 Follow-up in Meetings

The **Follow-up** tab in a meeting occurrence provides a consolidated view of action progress:

1. Open a meeting occurrence → **Follow-up** tab.
2. For each action linked to the meeting:
   - View the current status and completion percentage.
   - See **comments** from this and previous occurrences.
   - Add a new **comment** using the text area below each action.
3. Navigate to previous occurrence follow-ups to see historical discussion threads.

### 6.3 Adding Comments

Comments provide threaded discussion on individual actions within a meeting context.

1. In the meeting **Follow-up** tab, find the action you want to comment on.
2. Type your comment in the text area labeled *"Add a comment for [Action Title]..."*.
3. Click **Submit**.
4. The comment appears with your name and timestamp.

**Comment permissions:**
- You can **edit** or **delete** your own comments.
- **Admin** users can edit or delete any comment.

---

## 7. Status Workflow

Actions follow a defined status workflow. Only certain transitions are allowed:

| Current Status | Allowed Next Status |
|----------------|-------------------|
| **Open** | In Progress, On Hold, Cancelled |
| **In Progress** | On Hold, Done, Cancelled |
| **On Hold** | Open, In Progress, Cancelled |
| **Done** | *(Terminal — no further changes)* |
| **Cancelled** | *(Terminal — no further changes)* |

- When changing status to **Cancelled**, a **Cancel Reason** is required.
- When changing status to **On Hold**, a **Hold Reason** is required.
- **Done** and **Cancelled** are terminal states — once set, the status cannot be changed.

---

## 8. Dashboards

### 8.1 Personal Dashboard

Access via **Dashboard → Personal Dashboard**. Shows actions where you are the Lead.

| Tab | Content |
|-----|---------|
| **Overview** | 4 KPI cards (total, overdue, due soon, completed), sections for overdue actions, due soon, recently completed, and pending assignments |
| **By Deadline** | Actions sorted by deadline date |
| **By Category** | Actions grouped by business theme with per-category KPI summaries |
| **Gantt** | Timeline visualization of your actions |
| **Workload** | 16-week forecast chart and resource workload heatmap |

### 8.2 Global Dashboard

Access via **Dashboard → Global Dashboard**. Shows platform-wide KPIs and action statistics across all teams and business themes.

### 8.3 Team Dashboard

Access via **Dashboard → Team Dashboard**. Available to **Team Leads** and **Admins** only.

| Tab | Content |
|-----|---------|
| **Overview** | Team-level KPIs and summary statistics |
| **By Lead** | Actions grouped by team member |
| **By Category** | Actions grouped by business theme |

*Note: Team Leads can only view dashboards for teams they belong to. Admins can view any team.*

---

## 9. Quick Reference

| Task | Where to Go |
|------|-------------|
| Create a meeting series | Meeting Series → New Series |
| Schedule a meeting | Series Detail → Occurrences → pick date → Create Occurrence |
| Create an action from a meeting | Meeting Detail → Actions tab → New Action |
| Create a standalone action | Actions → New Action |
| Update action progress | Action Detail → Progress Update widget |
| Add a comment on an action | Meeting Detail → Follow-up tab → comment text area |
| Create a decision | Decisions → Add Decision *or* Meeting Detail → Decisions tab → Add Decision |
| View your workload | Dashboard → Personal Dashboard → Workload tab |
| Filter actions by Lead | Actions → Lead dropdown (shows your team members) |
| Switch language | Click EN/ZH in the navigation bar |
| Switch theme | Click the theme toggle (sun/moon icon) in the navigation bar |
