# ActionHub — Security & Access Control

> **Status**: Requirements-level specification  
> **Current-state note**: ActionHub currently runs as a JWT-authenticated React SPA over Flask APIs. Older session-cookie and staged V1/V1.1 language below is historical unless restated in the current-state sections.  
> **Depends on**: `R01_entities.md` (User entity), `R00_initial_vision.md` (stakeholders)  
> **Decisions**: D76–D88 in `DECISIONS.md`  
> **Consumed by**: `S16_API_Contract.md`, frontend auth implementation, route authorization

---

## §1 Overview

> **⚠️ CRITICAL — NO DATA-LEVEL SECURITY**
>
> ActionHub does **not provide comprehensive confidential-data security**. The product must not be treated as a confidential-data system.
> Visibility is broad for many operational surfaces, but selected meeting/action flows apply scoped visibility rules. There is **no platform-wide row-level security model**.
>
> **Users must NOT enter confidential, sensitive, or personally identifiable information (PII) into ActionHub.**
> Treat all content as potentially organization-visible and unsuitable for confidential use.
>
> **重要提示：本系统不提供数据级安全控制。**
> 本系统不适用于机密数据场景。虽然很多运营信息对已认证用户可见，但部分会议/行动流转采用范围限制；系统仍不提供统一的行级安全模型。
> **用户不得在 ActionHub 中输入机密、敏感或个人身份信息。**

ActionHub is an internal operational application. The live runtime uses username/password authentication with JWT access and refresh tokens for the SPA. Access control is admin-centric in the current frontend, with some `TeamLead` compatibility checks still present in backend services. Many dashboard and reference surfaces are broadly visible to authenticated users, while selected action and meeting flows apply scoped visibility rules.

### MVP (1.5-day) Scope

| Feature | MVP | V1.1 |
|---------|:---:|:----:|
| Simple username/password (bcrypt) | ✅ | |
| JWT Bearer auth for SPA APIs | ✅ | |
| Session timeout (8h) | ✅ | |
| Account lockout (5 failures) | ✅ | |
| Basic role check (Admin vs Member) | ✅ | |
| Full RBAC (4 roles × 18 operations) | | ✅ |
| Windows AD/LDAP integration | | ✅ |
| AD user sync (nightly batch) | | ✅ |
| CSRF protection | ✅ | |
| Audit logging | | ✅ (full) |

> **Current-state clarification**: The current product should be documented primarily as `Admin` versus authenticated user in the SPA. `TeamLead` remains a compatibility role in parts of the backend, but the product UX does not yet expose a fully distinct four-role experience.

> **Admin UX note**: In Admin User Management, the role field includes `TeamLead` as a selectable role value for user creation and editing.

---

## §2 Authentication Architecture

### §2.1 Authentication Method

**Current runtime (React SPA):**

| Aspect | Current behavior |
|--------|------------------|
| Login | Username + password against local ActionHub users |
| API auth | `Authorization: Bearer <access_token>` |
| Refresh | `/api/auth/refresh` |
| Frontend storage | `sessionStorage` |
| Logout | token invalidation + local session clear |

The server-side session model documented below is historical and must not be treated as the primary SPA authentication architecture.

**Day 1 (V1 MVP): Simple Username/Password (D76a)**

| Aspect | Decision |
|--------|----------|
| Protocol | Local username + bcrypt-hashed password in SQLite |
| Session | Server-side session with HTTP-only cookie |
| Session timeout | 8 hours (business day) (D77) |
| Admin creates accounts | Admin creates users manually with temp password |
| Password change | User can change own password from Settings |

**V1.1 (Week 2): Windows AD/LDAP Integration (D76b)**

| Aspect | Decision |
|--------|----------|
| Protocol | LDAP bind against Windows AD |
| Session | Same server-side session model |
| Password management | Managed in AD, not in ActionHub |
| Fallback | If AD unavailable, local admin account still works |

### §2.2 Login Flow

**Day 1 (Simple Auth):**
```
User opens ActionHub URL in browser
 → Login page: username + password
 → Server verifies bcrypt hash in SQLite
 → Success:
    → Create server-side session
    → Redirect to Personal Dashboard
 → Failure:
    → Show error "Invalid credentials"
    → Log failed attempt
    → After 5 failures in 15 minutes: temporary lockout 30 minutes (D78)
```

**V1.1 (AD Auth):**
```
User opens ActionHub URL in browser
 → Login page: username + password
 → Server performs LDAP bind against AD
 → Success:
    → Fetch user attributes from AD (displayName, mail, team, memberOf)
    → Match or create local User record
    → Create server-side session
    → Redirect to Personal Dashboard
 → Failure:
    → Show error "Invalid credentials" (no detail leak)
    → Log failed attempt
    → After 5 failures in 15 minutes: temporary lockout 30 minutes (D78)
```

### §2.3 AD User Sync (V1.1) (D79)

| Aspect | Behavior |
|--------|----------|
| Sync trigger | On login (real-time) + nightly batch job |
| Fields synced | displayName, mail, team, memberOf (groups), accountStatus |
| New user | Auto-created on first login with role = Member (D80) |
| Disabled in AD | `is_active` set to false; existing sessions invalidated |
| Team mapping | AD `team` attribute → ActionHub Team (admin-configurable mapping table) |
| Fallback mode | If AD unreachable, existing local accounts still work |

---

## §3 Authorization Model (RBAC)

### §3.1 Roles (D81)

**Current guidance**:

- `Admin` is the main elevated role in the SPA.
- Authenticated users can access the daily working modules.
- `TeamLead` is still recognized in parts of backend compatibility logic, but should not be documented as a fully distinct frontend capability surface unless and until the SPA reflects it consistently.

| Role | Description | Assignment |
|------|-------------|------------|
| **Admin** | Full system access, taxonomy config, user role management | Manual by Admin |
| **TeamLead** | Create/manage actions, assign within any scope, approve closures | Manual by Admin |
| **Member** | Execute actions, update own assignments, create actions | Default on first login |
| **ReadOnly** | View all dashboards and actions, no modifications | Manual by Admin |

### §3.2 Permission Matrix (D82)

| Operation | Admin | TeamLead | Member | ReadOnly |
|-----------|-------|----------|--------|----------|
| View any action | ✅ | ✅ | ✅ | ✅ |
| View any dashboard | ✅ | ✅ | ✅ | ✅ |
| Create action | ✅ | ✅ | ✅ | ❌ |
| Edit own action (as Lead) | ✅ | ✅ | ✅ | ❌ |
| Edit any action | ✅ | ✅ | ❌ | ❌ |
| Delete action | ✅ | ❌ | ❌ | ❌ |
| Assign any user | ✅ | ✅ | ❌ | ❌ |
| Assign within own team | ✅ | ✅ | ✅ | ❌ |
| Accept/decline own assignment | ✅ | ✅ | ✅ | ❌ |
| Change action status (as delegate) | ✅ | ✅ | ✅ | ❌ |
| Approve closure (as Lead) | ✅ | ✅ | ✅ | ❌ |
| Change Lead | ✅ | ❌ | ❌ | ❌ |
| Bulk operations | ✅ | ✅ | ❌ | ❌ |
| Manage taxonomy | ✅ | ❌ | ❌ | ❌ |
| Manage user roles | ✅ | ❌ | ❌ | ❌ |
| Configure notifications | ✅ | ❌ | ❌ | ❌ |
| Manage report schedules | ✅ | ✅ | ❌ | ❌ |
| Export reports | ✅ | ✅ | ✅ | ✅ |
| Upload meeting memo | ✅ | ✅ | ✅ | ❌ |
| Import seed data | ✅ | ❌ | ❌ | ❌ |
| Admin inline-edit actions table | ✅ | ✅ | ❌ | ❌ |

### §3.3 Data Visibility

| Rule | Behavior |
|------|----------|
| Most dashboards / reference views visible | Broad authenticated visibility remains the default model |
| Filter by team | UI provides team filter, not access restriction |
| Actions menu visibility | **Only show:** (1) My actions (created/owned/assigned), (2) Actions of my team members from non-private meetings, (3) Actions from meetings (public or private) where I am a participant. |
| Private actions / meetings | Limited private visibility exists in selected flows, but not as platform-wide row-level security |
| Sensitive actions | Not supported as a secure confidential-data model |

---

## §4 Session Management

### §4.1 Session Security (D84)

For the current SPA runtime, token handling is implemented through JWT access and refresh tokens rather than a primary `session_id` cookie model.

| Parameter | Value |
|-----------|-------|
| Access token storage | `sessionStorage` + in-memory React state |
| Refresh token storage | `sessionStorage` + in-memory React state |
| API auth transport | `Authorization: Bearer <access_token>` |
| Concurrent browser tabs | Allowed; each tab restores from `sessionStorage` |
| Session invalidation | Logout, refresh failure, timeout, account disabled |

### §4.2 CSRF Protection (D85)

- Current SPA/API runtime uses Bearer tokens rather than cookie-authenticated form posts, so classic CSRF tokens are not the primary protection model.
- The current security posture depends on JWT validation, short-lived access tokens, refresh-token handling, input validation, and XSS discipline.
- If future browser flows introduce cookie-authenticated endpoints again, CSRF controls must be specified for those endpoints explicitly rather than assumed globally.

---

## §5 Audit Logging

### §5.1 Events Logged (D86)

| Event Category | Examples |
|----------------|----------|
| Authentication | Login success, login failure, logout, session timeout |
| Authorization | Permission denied (who, what, when) |
| Data modification | Action create/update/delete, assignment changes |
| Admin operations | Role changes, taxonomy updates, import operations |
| Report access | Report generated, report exported |

### §5.2 Audit Log Fields

| Field | Type |
|-------|------|
| id | INT (PK) |
| timestamp | DATETIME |
| user_id | FK → User |
| ip_address | VARCHAR(45) |
| event_category | ENUM |
| event_type | VARCHAR(100) |
| resource_type | VARCHAR(50) (Action, User, etc.) |
| resource_id | INT |
| details | JSON |
| success | BOOLEAN |

### §5.3 Audit Retention (D87)

- Audit logs retained for 3 years minimum
- Read-only (no modification or deletion except by DBA)
- Queryable by Admin via admin panel

---

## §6 Network & Infrastructure Security (D88)

| Aspect | Requirement |
|--------|-------------|
| Transport | HTTPS recommended (self-signed cert acceptable for LAN) |
| Server access | Windows server secured per corporate IT policy |
| Database | SQLite file with restricted OS-level permissions (owner = app service account) |
| Backup | Daily SQLite file copy; backup location access-restricted |
| File uploads | Stored outside webroot; served through application (no direct URL) |
| Input validation | All user inputs sanitized; parameterized queries only |
| Dependencies | Regular security updates for framework + libraries |
