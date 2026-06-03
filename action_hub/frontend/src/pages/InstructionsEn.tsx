import React from "react";
import { Table, Badge } from "react-bootstrap";

/* ───────────────────── Section labels ───────────────────── */
export const SECTION_LABELS_EN: Record<string, string> = {
  overview: "1. Overview",
  meetingSeries: "2. Meeting Series",
  meetingOccurrences: "3. Meeting Occurrences",
  actions: "4. Actions",
  decisions: "5. Decisions",
  followUp: "6. Follow-up & Comments",
  statusWorkflow: "7. Status Workflow",
  dashboards: "8. Dashboards",
  quickRef: "Quick Reference",
};

/* ───────────────────── Section content ───────────────────── */

function SectionOverview() {
  return (
    <>
      <p>
        ActionHub is a web-based action-tracking platform that replaces Excel logbooks with a unified
        system for managing actions, meetings, decisions, and dashboards. It supports bilingual
        operation (English / Chinese).
      </p>

      <h4>Key Features</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Feature</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><strong>Meeting Series</strong></td><td>Organize recurring meetings with default participants, access control, and create individual occurrences with agendas, actions, decisions, and memos</td></tr>
          <tr><td><strong>Action Management</strong></td><td>Create, assign, and track actions with status workflows, deadlines, priorities, Lead assignment, and progress updates</td></tr>
          <tr><td><strong>Decision Tracking</strong></td><td>Record decisions with context, rationale, revision history, and lifecycle management</td></tr>
          <tr><td><strong>Dashboards</strong></td><td>Personal, Team, and Global dashboards with KPIs, deadline views, Gantt charts, and workload forecasts</td></tr>
          <tr><td><strong>Progress Follow-up</strong></td><td>Update action completion percentage, add comments, and flag blockers within meeting context</td></tr>
          <tr><td><strong>Access Control</strong></td><td>Private meeting series restrict content visibility to the creator and listed participants only</td></tr>
          <tr><td><strong>Notifications</strong></td><td>In-app alerts for assignments, status changes, and approaching deadlines</td></tr>
          <tr><td><strong>Export</strong></td><td>Export actions and meeting data to Excel/PDF</td></tr>
          <tr><td><strong>Bilingual UI</strong></td><td>Switch between English and Chinese using the language selector in the navigation bar</td></tr>
        </tbody>
      </Table>

      <h4>User Roles &amp; Access</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Role</th><th>Access</th></tr></thead>
        <tbody>
          <tr><td><Badge bg="danger">Admin</Badge></td><td>Full access — manage users, teams, business themes, view all dashboards, and perform all operations</td></tr>
          <tr><td><Badge bg="primary">Team Lead</Badge></td><td>Standard access plus Team Dashboard for their own team(s)</td></tr>
          <tr><td><Badge bg="success">Member</Badge></td><td>Create and manage actions, participate in meetings, access Personal and Global dashboards</td></tr>
          <tr><td><Badge bg="secondary">Read Only</Badge></td><td>View-only access to actions, meetings, decisions, and dashboards</td></tr>
        </tbody>
      </Table>

      <h4>Logging In</h4>
      <ol>
        <li>Navigate to the ActionHub URL in your browser.</li>
        <li>Enter your <strong>Username</strong> and <strong>Password</strong>.</li>
        <li>Click <strong>Login</strong>.</li>
        <li>To change your password: use the user menu (top-right) → <strong>Change Password</strong>.</li>
      </ol>

      <h4>Navigation</h4>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>Menu Item</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td><strong>Meeting Series</strong></td><td>List and manage meeting series and their occurrences</td></tr>
          <tr><td><strong>Actions</strong></td><td>View, create, and manage actions</td></tr>
          <tr><td><strong>Decisions</strong></td><td>View, create, and manage decisions</td></tr>
          <tr><td><strong>Dashboard</strong></td><td>Dropdown: Personal Dashboard, Global Dashboard, Team Dashboard</td></tr>
          <tr><td><strong>Admin</strong></td><td><em>(Admin only)</em> Manage Users, Teams, and Business Themes</td></tr>
          <tr><td><strong>Instructions</strong></td><td>This help page</td></tr>
        </tbody>
      </Table>
      <p className="mt-2 text-muted">
        The right side of the navigation bar also contains: <strong>Notification bell</strong>,{" "}
        <strong>Theme toggle</strong> (light/dark), <strong>Language selector</strong> (EN/ZH), and{" "}
        <strong>User menu</strong> (profile, change password, logout).
      </p>
    </>
  );
}

function SectionMeetingSeries() {
  return (
    <>
      <p>
        A <strong>Meeting Series</strong> groups related meetings (e.g., weekly team stand-ups, monthly
        reviews). It defines the topic, default participants, and business theme.
      </p>

      <h4>Viewing Meeting Series</h4>
      <p>Click <strong>Meeting Series</strong> in the navigation bar to see all series.</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Column</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Title</td><td>Name of the series</td></tr>
          <tr><td>Category</td><td>Business theme the series belongs to</td></tr>
          <tr><td>Occurrences</td><td>Number of meetings held in this series</td></tr>
          <tr><td>Access</td><td>Shows a <Badge bg="success" className="mx-1">Public</Badge> or <Badge bg="warning" text="dark" className="mx-1">Private</Badge> badge — private series are restricted to creator and participants</td></tr>
          <tr><td>Created</td><td>Date the series was created</td></tr>
        </tbody>
      </Table>

      <h4>Creating a New Meeting Series</h4>
      <ol>
        <li>On the Meeting Series list page, click <strong>"New Series"</strong>.</li>
        <li>Fill in the form:</li>
      </ol>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Title</td><td><Badge bg="danger">Yes</Badge></td><td>Name of the meeting series (e.g., "Weekly Engineering Sync")</td></tr>
          <tr><td>Category</td><td>No</td><td>Business theme to associate with this series</td></tr>
          <tr><td>Description</td><td>No</td><td>Purpose or scope of the meeting series</td></tr>
        </tbody>
      </Table>
      <ol start={3}>
        <li>Click <strong>Save</strong>. You will be taken to the series detail page.</li>
      </ol>

      <h4>Managing Series Details</h4>
      <p>On the series detail page you can:</p>
      <ul>
        <li><strong>Edit</strong> the title, description, category, and visibility settings.</li>
        <li>
          <strong>Manage Default Participants</strong>: Add or remove users automatically included in
          new occurrences. Each participant can be:
          <ul>
            <li><strong>Compulsory</strong> — always required to attend</li>
            <li><strong>Optional</strong> — invited but attendance not mandatory</li>
          </ul>
        </li>
      </ul>

      <h4>Access Control</h4>
      <p>Meeting series support <strong>Public</strong> and <strong>Private</strong> visibility:</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Visibility</th><th>Behaviour</th></tr></thead>
        <tbody>
          <tr><td><Badge bg="success">Public</Badge></td><td>Any logged-in user can view the series, its occurrences, and all linked content (actions, decisions, memos)</td></tr>
          <tr><td><Badge bg="warning" text="dark">Private</Badge></td><td>Only the <strong>series creator</strong> and <strong>listed participants</strong> can access the detail page. Other users see a <strong>lock screen</strong> with the series title and a message to contact the creator</td></tr>
        </tbody>
      </Table>
      <p>On the series list page, private series you cannot access display a <strong>lock icon</strong> (🔒) instead of a clickable link.</p>

      <h4>Creating a Meeting Occurrence</h4>
      <ol>
        <li>Open the series detail page.</li>
        <li>In the <strong>Occurrences</strong> section, select a date using the date picker.</li>
        <li>Click <strong>Create Occurrence</strong>.</li>
        <li>The new occurrence appears in the table with: Date, Status, Actions count, Decisions count.</li>
      </ol>
    </>
  );
}

function SectionMeetingOccurrences() {
  return (
    <>
      <p>
        A meeting occurrence is a single session within a series. It provides a workspace for managing
        actions, decisions, memos, and follow-up discussions.
      </p>

      <h4>Meeting Detail Tabs</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Tab</th><th>Purpose</th></tr></thead>
        <tbody>
          <tr><td><strong>Overview</strong></td><td>Meeting date, series info, summary, and participants list</td></tr>
          <tr><td><strong>Actions</strong></td><td>Actions linked to this meeting — create new or review existing</td></tr>
          <tr><td><strong>Decisions</strong></td><td>Decisions made during this meeting</td></tr>
          <tr><td><strong>Memos</strong></td><td>Free-text notes and meeting minutes</td></tr>
          <tr><td><strong>Follow-up</strong></td><td>Review progress on actions, add comments, view history from previous occurrences</td></tr>
        </tbody>
      </Table>

      <h4>Adding a Memo</h4>
      <ol>
        <li>Go to the <strong>Memos</strong> tab.</li>
        <li>Click <strong>"Add Memo"</strong>.</li>
        <li>Enter the memo <strong>Title</strong> and <strong>Content</strong>.</li>
        <li>Click <strong>Save</strong>.</li>
      </ol>
    </>
  );
}

function SectionActions() {
  return (
    <>
      <p>Actions are trackable work items with an owner (Lead), deadline, status, and progress tracking.</p>

      <h4>Viewing Actions</h4>
      <p>Click <strong>Actions</strong> in the navigation bar. The list displays all actions with the following columns:</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Column</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Title</td><td>Action title. If the action is linked to a <strong>private meeting series</strong> you are not a member of, the title is <strong>blurred</strong> with a 🔒 indicator</td></tr>
          <tr><td>Lead</td><td>The person responsible for the action (owner)</td></tr>
          <tr><td>Status</td><td>Current status badge</td></tr>
          <tr><td>Deadline</td><td>Target completion date</td></tr>
          <tr><td>Category</td><td>Business theme</td></tr>
        </tbody>
      </Table>

      <h4>Filters</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Filter</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Search</td><td>Free-text search by title</td></tr>
          <tr><td>Status</td><td>Filter by status (Open, In Progress, On Hold, Done, Cancelled)</td></tr>
          <tr><td>Category</td><td>Filter by business theme</td></tr>
          <tr><td>Series</td><td>Filter by meeting series</td></tr>
          <tr><td>Lead</td><td>Filter by Lead — dropdown shows <strong>your team members</strong> only</td></tr>
          <tr><td>My Lead</td><td>Toggle to show only actions where you are the Lead (on by default)</td></tr>
          <tr><td>Hide Closed</td><td>Toggle to hide Done/Cancelled actions</td></tr>
        </tbody>
      </Table>

      <h4>Private Series Actions</h4>
      <p>
        Actions linked to a <strong>private meeting series</strong> are subject to access control.
        If you are <strong>not</strong> the series creator or a participant:
      </p>
      <ul>
        <li>The action title appears <strong>blurred</strong> with a 🔒 lock indicator.</li>
        <li>You cannot open the action detail page.</li>
        <li>This ensures confidential meeting content remains protected.</li>
      </ul>

      <h4>Creating an Action — from the Actions List (standalone)</h4>
      <ol>
        <li>Click <strong>"New Action"</strong> on the Actions list page.</li>
        <li>Fill in the form:</li>
      </ol>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Title</td><td><Badge bg="danger">Yes</Badge></td><td>Short description of the action</td></tr>
          <tr><td>Status</td><td>No</td><td>Initial status (defaults to Open)</td></tr>
          <tr><td>Description</td><td>No</td><td>Detailed description</td></tr>
          <tr><td>Tags</td><td>No</td><td>Comma-separated keywords</td></tr>
          <tr><td>Deadline</td><td>No</td><td>Target completion date</td></tr>
          <tr><td>Category</td><td>No</td><td>Business theme</td></tr>
          <tr><td>Lead</td><td>Auto</td><td>Automatically set to the creator</td></tr>
        </tbody>
      </Table>
      <ol start={3}><li>Click <strong>Save</strong>.</li></ol>

      <h4>Creating an Action — from a Meeting Occurrence</h4>
      <ol>
        <li>Open a meeting occurrence and go to the <strong>Actions</strong> tab.</li>
        <li>Click <strong>"New Action"</strong>. The meeting context is auto-linked.</li>
        <li>The <strong>Lead</strong> field is selectable from the meeting participants list.</li>
      </ol>

      <h4>Editing an Action</h4>
      <p>Open the action detail page and click <strong>Edit</strong>:</p>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>Field</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Title</td><td>Edit the action title</td></tr>
          <tr><td>Status</td><td>Change status (following allowed transitions — see Status Workflow section)</td></tr>
          <tr><td>Priority</td><td>Set High / Medium / Low</td></tr>
          <tr><td>Deadline</td><td>Update the target date</td></tr>
          <tr><td>Description</td><td>Modify the detailed description</td></tr>
          <tr><td>Cancel Reason</td><td><em>Required when cancelling</em> — explain why the action is cancelled</td></tr>
          <tr><td>Hold Reason</td><td><em>Required when putting on hold</em> — explain why the action is paused</td></tr>
        </tbody>
      </Table>
    </>
  );
}

function SectionDecisions() {
  return (
    <>
      <p>Decisions record formal outcomes with context, rationale, and a full revision history.</p>

      <h4>Viewing Decisions</h4>
      <p>Click <strong>Decisions</strong> in the navigation bar. Filters available:</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Filter</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Search</td><td>Free-text search</td></tr>
          <tr><td>Status</td><td>Published or Expired</td></tr>
          <tr><td>Series</td><td>Filter by meeting series</td></tr>
          <tr><td>Category</td><td>Filter by business theme</td></tr>
          <tr><td>Creator</td><td>Filter by who created the decision</td></tr>
        </tbody>
      </Table>

      <h4>Creating a Decision</h4>
      <p>Decisions can be created standalone (from the Decisions list → <strong>"Add Decision"</strong>) or from within a meeting occurrence (Decisions tab → <strong>"Add Decision"</strong>).</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Field</th><th>Required</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Title</td><td><Badge bg="danger">Yes</Badge></td><td>Short summary of the decision</td></tr>
          <tr><td>Status</td><td>No</td><td>Published (default) or Expired</td></tr>
          <tr><td>Content</td><td>No</td><td>Full text of the decision</td></tr>
          <tr><td>Context</td><td>No</td><td>Background information and circumstances</td></tr>
          <tr><td>Reason</td><td>No</td><td>Rationale — why this decision was made</td></tr>
          <tr><td>Tags</td><td>No</td><td>Comma-separated keywords</td></tr>
          <tr><td>Category</td><td>No</td><td>Business theme</td></tr>
        </tbody>
      </Table>

      <h4>Editing a Decision</h4>
      <ol>
        <li>Open the decision detail page and click <strong>Edit</strong>.</li>
        <li>Modify any fields and click <strong>Save</strong>.</li>
        <li>Each edit creates a new <strong>revision</strong> — full history is preserved in the Revision History section.</li>
      </ol>

      <h4>Changing Decision Status</h4>
      <p><strong>Published → Expired:</strong> When a decision is no longer in effect. Status changes are made from the decision detail page.</p>
    </>
  );
}

function SectionFollowUp() {
  return (
    <>
      <h4>Updating Progress on an Action</h4>
      <p>Open the action detail page and use the <strong>Progress Update</strong> widget:</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Field</th><th>Description</th></tr></thead>
        <tbody>
          <tr><td>Completion %</td><td>Drag the slider from 0% to 100% to indicate progress</td></tr>
          <tr><td>Status</td><td>Select the current status from the dropdown</td></tr>
          <tr><td>Comment</td><td>Add a note about what was done or what's next</td></tr>
          <tr><td>Blockers</td><td>Describe any obstacles preventing progress</td></tr>
        </tbody>
      </Table>
      <p>Click <strong>Update Progress</strong>. The update is recorded with your name and timestamp. All previous updates are visible in the feedback history.</p>

      <h4>Follow-up in Meetings</h4>
      <p>The <strong>Follow-up</strong> tab in a meeting occurrence provides a consolidated view of action progress:</p>
      <ol>
        <li>Open a meeting occurrence → <strong>Follow-up</strong> tab.</li>
        <li>For each action: view current status, completion %, and comments from this and previous occurrences.</li>
        <li>Add a new comment using the text area below each action.</li>
        <li>Navigate to previous occurrence follow-ups to see historical discussion threads.</li>
      </ol>

      <h4>Adding Comments</h4>
      <ol>
        <li>In the meeting <strong>Follow-up</strong> tab, find the action to comment on.</li>
        <li>Type in the text area labeled <em>"Add a comment for [Action Title]..."</em></li>
        <li>Click <strong>Submit</strong>.</li>
        <li>The comment appears with your name and timestamp.</li>
      </ol>
      <p><strong>Comment permissions:</strong> You can edit or delete your own comments. Admin users can edit or delete any comment.</p>
    </>
  );
}

function SectionStatusWorkflow() {
  return (
    <>
      <p>Actions follow a defined status workflow. Only certain transitions are allowed:</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Current Status</th><th>Allowed Next Status</th></tr></thead>
        <tbody>
          <tr>
            <td><Badge bg="secondary">Open</Badge></td>
            <td>
              <Badge bg="primary" className="me-1">In Progress</Badge>
              <Badge bg="warning" text="dark" className="me-1">On Hold</Badge>
              <Badge bg="dark">Cancelled</Badge>
            </td>
          </tr>
          <tr>
            <td><Badge bg="primary">In Progress</Badge></td>
            <td>
              <Badge bg="warning" text="dark" className="me-1">On Hold</Badge>
              <Badge bg="success" className="me-1">Done</Badge>
              <Badge bg="dark">Cancelled</Badge>
            </td>
          </tr>
          <tr>
            <td><Badge bg="warning" text="dark">On Hold</Badge></td>
            <td>
              <Badge bg="secondary" className="me-1">Open</Badge>
              <Badge bg="primary" className="me-1">In Progress</Badge>
              <Badge bg="dark">Cancelled</Badge>
            </td>
          </tr>
          <tr>
            <td><Badge bg="success">Done</Badge></td>
            <td><em className="text-muted">Terminal — no further changes</em></td>
          </tr>
          <tr>
            <td><Badge bg="dark">Cancelled</Badge></td>
            <td><em className="text-muted">Terminal — no further changes</em></td>
          </tr>
        </tbody>
      </Table>
      <ul>
        <li>When changing status to <strong>Cancelled</strong>, a <strong>Cancel Reason</strong> is required.</li>
        <li>When changing status to <strong>On Hold</strong>, a <strong>Hold Reason</strong> is required.</li>
        <li><strong>Done</strong> and <strong>Cancelled</strong> are terminal states — once set, the status cannot be changed.</li>
      </ul>
    </>
  );
}

function SectionDashboards() {
  return (
    <>
      <h4>Personal Dashboard</h4>
      <p>Access via <strong>Dashboard → Personal Dashboard</strong>. Shows actions where you are the Lead.</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>Tab</th><th>Content</th></tr></thead>
        <tbody>
          <tr><td><strong>Overview</strong></td><td>4 KPI cards (total, overdue, due soon, completed), sections for overdue actions, due soon, recently completed, and pending assignments</td></tr>
          <tr><td><strong>By Deadline</strong></td><td>Actions sorted by deadline date</td></tr>
          <tr><td><strong>By Category</strong></td><td>Actions grouped by business theme with per-category KPI summaries</td></tr>
          <tr><td><strong>Gantt</strong></td><td>Timeline visualization of your actions</td></tr>
          <tr><td><strong>Workload</strong></td><td>16-week forecast chart and resource workload heatmap</td></tr>
        </tbody>
      </Table>

      <h4>Global Dashboard</h4>
      <p>Access via <strong>Dashboard → Global Dashboard</strong>. Shows platform-wide KPIs and action statistics across all teams and business themes.</p>

      <h4>Team Dashboard</h4>
      <p>Access via <strong>Dashboard → Team Dashboard</strong>. Available to <strong>Team Leads</strong> and <strong>Admins</strong> only.</p>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>Tab</th><th>Content</th></tr></thead>
        <tbody>
          <tr><td><strong>Overview</strong></td><td>Team-level KPIs and summary statistics</td></tr>
          <tr><td><strong>By Lead</strong></td><td>Actions grouped by team member</td></tr>
          <tr><td><strong>By Category</strong></td><td>Actions grouped by business theme</td></tr>
        </tbody>
      </Table>
      <p className="mt-2 text-muted"><em>Team Leads can only view dashboards for teams they belong to. Admins can view any team.</em></p>
    </>
  );
}

function SectionQuickRef() {
  return (
    <>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>Task</th><th>Where to Go</th></tr></thead>
        <tbody>
          <tr><td>Create a meeting series</td><td>Meeting Series → New Series</td></tr>
          <tr><td>Schedule a meeting</td><td>Series Detail → Occurrences → pick date → Create Occurrence</td></tr>
          <tr><td>Create an action from a meeting</td><td>Meeting Detail → Actions tab → New Action</td></tr>
          <tr><td>Create a standalone action</td><td>Actions → New Action</td></tr>
          <tr><td>Update action progress</td><td>Action Detail → Progress Update widget</td></tr>
          <tr><td>Add a comment on an action</td><td>Meeting Detail → Follow-up tab → comment text area</td></tr>
          <tr><td>Create a decision</td><td>Decisions → Add Decision  <em>or</em>  Meeting Detail → Decisions tab → Add Decision</td></tr>
          <tr><td>View your workload</td><td>Dashboard → Personal Dashboard → Workload tab</td></tr>
          <tr><td>Filter actions by Lead</td><td>Actions → Lead dropdown (shows your team members)</td></tr>
          <tr><td>Switch language</td><td>Click EN/ZH in the navigation bar</td></tr>
          <tr><td>Switch theme</td><td>Click the theme toggle (sun/moon icon) in the navigation bar</td></tr>
        </tbody>
      </Table>
    </>
  );
}

export const SECTION_COMPONENTS_EN: Record<string, React.FC> = {
  overview: SectionOverview,
  meetingSeries: SectionMeetingSeries,
  meetingOccurrences: SectionMeetingOccurrences,
  actions: SectionActions,
  decisions: SectionDecisions,
  followUp: SectionFollowUp,
  statusWorkflow: SectionStatusWorkflow,
  dashboards: SectionDashboards,
  quickRef: SectionQuickRef,
};
