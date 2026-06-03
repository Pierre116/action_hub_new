INSERT OR IGNORE INTO t_department (dep_code, dep_name_en, dep_name_cn, dep_desc) VALUES
('FAC', 'Facility', '设施部', 'Building, utilities and infrastructure management'),
('IE', 'Industrial Engineering', '工业工程部', 'Line balancing and process optimization'),
('CI', 'Continuous Improvement', '持续改善部', 'Lean and Kaizen initiatives'),
('PQ', 'Production Quality', '生产质量部', 'Production quality control and compliance'),
('IQC', 'Incoming Quality Control', '来料质检部', 'Incoming inspection and supplier part quality'),
('SQ', 'Supplier Quality', '供应商质量部', 'Supplier qualification and quality audits'),
('HP', 'Health & Safety', '健康与安全部', 'EHS and safety actions'),
('WH', 'Warehouse', '仓储部', 'Inventory and storage operations'),
('LOG', 'Logistics', '物流部', 'Inbound/outbound logistics'),
('SRC', 'Sourcing', '采购部', 'Supplier sourcing and management'),
('PROC', 'Procurement', '采购执行部', 'Purchase execution and PO follow-up'),
('ESL', 'Equipment Supply Leader', '设备供应负责人', 'Equipment procurement and supply lifecycle'),
('PLAN', 'Planning', '计划部', 'Production planning and scheduling'),
('CTO', 'Configuration to Order', '配置化订单部', 'Custom configuration and order engineering'),
('AT', 'Assembly and Testing', '装配与测试部', 'Product assembly, integration and final testing'),
('HPM', 'Heavy Parts Manufacturing', '重型零件制造部', 'Machining and fabrication of heavy structural parts');

-- Teams (mirror of departments after v2.6 teams-only migration)
-- INSERT OR IGNORE is idempotent once tea_code has a UNIQUE constraint (v2.9+)
INSERT OR IGNORE INTO t_team (tea_code, tea_name_en, tea_name_cn, tea_active, tea_sort_order) VALUES
('FAC',  'Facility',                   '设施部',         1, 1),
('IE',   'Industrial Engineering',      '工业工程部',     1, 2),
('CI',   'Continuous Improvement',       '持续改善部',     1, 3),
('PQ',   'Production Quality',           '生产质量部',     1, 4),
('IQC',  'Incoming Quality Control',     '来料质检部',     1, 5),
('SQ',   'Supplier Quality',             '供应商质量部',   1, 6),
('HP',   'Health & Safety',              '健康与安全部',   1, 7),
('WH',   'Warehouse',                    '仓储部',         1, 8),
('LOG',  'Logistics',                    '物流部',         1, 9),
('SRC',  'Sourcing',                     '采购部',         1, 10),
('PROC', 'Procurement',                  '采购执行部',     1, 11),
('ESL',  'Equipment Supply Leader',      '设备供应负责人', 1, 12),
('PLAN', 'Planning',                     '计划部',         1, 13),
('CTO',  'Configuration to Order',       '配置化订单部',   1, 14),
('AT',   'Assembly and Testing',         '装配与测试部',   1, 15),
('HPM',  'Heavy Parts Manufacturing',    '重型零件制造部', 1, 16),
('MGT',  'Management',                   '管理层',         1, 17);

INSERT OR IGNORE INTO t_topic (top_id, top_name, top_desc, top_active, top_is_global, top_sort) VALUES
(1, 'General', 'Default topic for actions and meetings', 1, 1, 0);

INSERT OR IGNORE INTO t_category (cat_name_en, cat_name_cn, cat_color) VALUES
('Supplier Issue', '供应商问题', '#EF5350'),
('Internal Process', '内部流程', '#42A5F5'),
('Design Change', '设计变更', '#AB47BC'),
('Quality Issue', '质量问题', '#FF7043'),
('Material Shortage', '物料短缺', '#26A69A'),
('System/Tool', '系统/工具', '#5C6BC0'),
('Training', '培训', '#9CCC65'),
('General', '通用', '#BDBDBD');
