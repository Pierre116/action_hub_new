"""Hardcoded pilot workflow: OT User Creation (O5/D175).

This will be extracted to a JSON graph in V2.1.
"""

OT_USER_CREATION_GRAPH = {
    "steps": {
        "request": {
            "name_en": "Request",
            "name_cn": "申请",
            "type": "Task",
            "order": 1,
            "role": "TeamLead",
            "sla_hours": None,
            "fields": [
                {
                    "key": "employee_name",
                    "label_en": "Employee Name",
                    "label_cn": "员工姓名",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "role",
                    "label_en": "Role",
                    "label_cn": "角色",
                    "type": "dropdown",
                    "options": ["Operator", "Technician", "Engineer"],
                    "required": True,
                },
                {
                    "key": "start_date",
                    "label_en": "Start Date",
                    "label_cn": "入职日期",
                    "type": "date",
                    "required": True,
                },
                {
                    "key": "workshop_zone",
                    "label_en": "Zone",
                    "label_cn": "车间区域",
                    "type": "dropdown",
                    "options": ["Zone A", "Zone B", "Zone C"],
                    "required": False,
                },
            ],
        },
        "facility": {
            "name_en": "Facility",
            "name_cn": "设施",
            "type": "Task",
            "order": 2,
            "role": "Facility",
            "sla_hours": 24,
            "fields": [
                {
                    "key": "badge_code",
                    "label_en": "Badge Code",
                    "label_cn": "工牌编号",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "card_printed",
                    "label_en": "Card Printed",
                    "label_cn": "卡片已打印",
                    "type": "checkbox",
                    "required": False,
                },
            ],
        },
        "hse_validation": {
            "name_en": "HSE Validation",
            "label_en": "HSE Validation",
            "name_cn": "HSE验证",
            "label_cn": "HSE验证",
            "type": "Task",
            "order": 2,
            "role": "HSE",
            "sla_hours": 48,
            "fields": [
                {
                    "key": "training_checklist",
                    "label_en": "Training Checklist",
                    "label_cn": "培训清单",
                    "type": "checklist",
                    "options": [
                        "Safety induction",
                        "Equipment-specific",
                        "PPE training",
                        "Emergency procedures",
                    ],
                    "required": True,
                },
            ],
        },
        "join": {
            "name_en": "Join",
            "name_cn": "合并",
            "type": "Join",
            "order": 3,
        },
        "finance": {
            "name_en": "Finance",
            "name_cn": "财务",
            "type": "Task",
            "order": 4,
            "role": "Finance",
            "sla_hours": 24,
            "fields": [
                {
                    "key": "sap_user_code",
                    "label_en": "SAP User Code",
                    "label_cn": "SAP用户代码",
                    "type": "text",
                    "required": True,
                },
            ],
        },
        "ot_admin": {
            "name_en": "OT Admin",
            "name_cn": "OT管理员",
            "type": "Task",
            "order": 5,
            "role": "OT",
            "sla_hours": 24,
            "fields": [
                {
                    "key": "timesheet_id",
                    "label_en": "Timesheet ID",
                    "label_cn": "考勤ID",
                    "type": "text",
                    "required": True,
                },
                {
                    "key": "sap_id_ref",
                    "label_en": "SAP ID Reference",
                    "label_cn": "SAP ID参考",
                    "type": "text",
                    "required": True,
                },
            ],
        },
        "active": {
            "name_en": "Active",
            "name_cn": "激活",
            "type": "End",
            "order": 6,
        },
    },
    "transitions": [
        {
            "from": "request",
            "to": "facility",
            "label_en": "Dispatch",
            "label_cn": "派发",
        },
        {
            "from": "request",
            "to": "hse_validation",
            "label_en": "Dispatch",
            "label_cn": "派发",
        },
        {"from": "facility", "to": "join", "label_en": "Done", "label_cn": "完成"},
        {
            "from": "hse_validation",
            "to": "join",
            "label_en": "Validated",
            "label_cn": "已验证",
        },
        {"from": "join", "to": "finance", "label_en": "Auto", "label_cn": "自动"},
        {
            "from": "finance",
            "to": "ot_admin",
            "label_en": "SAP code ready",
            "label_cn": "SAP代码就绪",
        },
        {
            "from": "ot_admin",
            "to": "active",
            "label_en": "Complete",
            "label_cn": "完成",
        },
    ],
    "bindings": [{"scope_type": "team", "scope_id": None}],
}

# Simple action workflow (default)
SIMPLE_ACTION_GRAPH = {
    "steps": {
        "open": {
            "name_en": "Open",
            "name_cn": "开放",
            "type": "Task",
            "order": 1,
            "fields": [],
        },
        "in_progress": {
            "name_en": "In Progress",
            "name_cn": "进行中",
            "type": "Task",
            "order": 2,
            "fields": [],
        },
        "done": {
            "name_en": "Done",
            "name_cn": "已完成",
            "type": "End",
            "order": 3,
            "fields": [],
        },
    },
    "transitions": [
        {"from": "open", "to": "in_progress", "label_en": "Start", "label_cn": "开始"},
        {"from": "in_progress", "to": "done", "label_en": "Complete", "label_cn": "完成"},
    ],
    "bindings": [],
}
