import React from "react";
import { Table, Badge } from "react-bootstrap";

/* ───────────────────── 侧边栏标签 ───────────────────── */
export const SECTION_LABELS_ZH: Record<string, string> = {
  overview: "1. 概览",
  meetingSeries: "2. 会议系列",
  meetingOccurrences: "3. 会议场次",
  actions: "4. 行动项",
  decisions: "5. 决议",
  followUp: "6. 跟进与评论",
  statusWorkflow: "7. 状态工作流",
  dashboards: "8. 仪表盘",
  quickRef: "快速参考",
};

/* ───────────────────── 各章节内容 ───────────────────── */

function SectionOverview() {
  return (
    <>
      <p>
        行动中心是一个基于网页的行动追踪平台，用统一的系统取代 Excel 台账，管理行动项、会议、决议和仪表盘。
        支持中英文双语操作。
      </p>

      <h4>核心功能</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>功能</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td><strong>会议系列</strong></td><td>组织定期会议，设定默认参会人、访问控制，并创建包含议题、行动项、决议和备忘录的单次会议</td></tr>
          <tr><td><strong>行动项管理</strong></td><td>创建、分配和跟踪行动项；支持状态流转、截止日期、优先级、负责人指定和进度更新</td></tr>
          <tr><td><strong>决议追踪</strong></td><td>记录决议及其背景、依据、修订历史和生命周期管理</td></tr>
          <tr><td><strong>仪表盘</strong></td><td>个人、团队和全局仪表盘，提供关键指标、截止日期视图、甘特图和工作量预测</td></tr>
          <tr><td><strong>进度跟进</strong></td><td>在会议中更新行动项完成百分比、添加评论和标记阻碍</td></tr>
          <tr><td><strong>访问控制</strong></td><td>私有会议系列仅对创建者和已列入的参会人可见</td></tr>
          <tr><td><strong>通知</strong></td><td>应用内提醒：新分配、状态变更和截止日期临近</td></tr>
          <tr><td><strong>导出</strong></td><td>将行动项和会议数据导出为 Excel / PDF</td></tr>
          <tr><td><strong>双语界面</strong></td><td>点击导航栏的语言选择器，在中文和英文之间切换</td></tr>
        </tbody>
      </Table>

      <h4>用户角色与权限</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>角色</th><th>权限</th></tr></thead>
        <tbody>
          <tr><td><Badge bg="danger">管理员</Badge></td><td>完全访问权限 — 管理用户、团队、业务主题，查看所有仪表盘并执行所有操作</td></tr>
          <tr><td><Badge bg="primary">团队负责人</Badge></td><td>标准访问权限，另可查看其所属团队的团队仪表盘</td></tr>
          <tr><td><Badge bg="success">成员</Badge></td><td>创建和管理行动项、参与会议、访问个人和全局仪表盘</td></tr>
          <tr><td><Badge bg="secondary">只读</Badge></td><td>仅可查看行动项、会议、决议和仪表盘</td></tr>
        </tbody>
      </Table>

      <h4>登录</h4>
      <ol>
        <li>在浏览器中访问行动中心的网址。</li>
        <li>输入<strong>用户名</strong>和<strong>密码</strong>。</li>
        <li>点击<strong>登录</strong>。</li>
        <li>修改密码：点击右上角用户菜单 → <strong>修改密码</strong>。</li>
      </ol>

      <h4>导航菜单</h4>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>菜单项</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td><strong>会议系列</strong></td><td>查看和管理会议系列及其各场次</td></tr>
          <tr><td><strong>行动项</strong></td><td>查看、创建和管理行动项</td></tr>
          <tr><td><strong>决议</strong></td><td>查看、创建和管理决议</td></tr>
          <tr><td><strong>仪表盘</strong></td><td>下拉菜单：个人仪表盘、全局仪表盘、团队仪表盘</td></tr>
          <tr><td><strong>管理</strong></td><td><em>（仅管理员）</em>管理用户、团队和业务主题</td></tr>
          <tr><td><strong>说明</strong></td><td>本帮助页面</td></tr>
        </tbody>
      </Table>
      <p className="mt-2 text-muted">
        导航栏右侧还包含：<strong>通知铃铛</strong>、
        <strong>主题切换</strong>（明/暗）、<strong>语言选择器</strong>（中/英）和
        <strong>用户菜单</strong>（个人资料、修改密码、退出登录）。
      </p>
    </>
  );
}

function SectionMeetingSeries() {
  return (
    <>
      <p>
        <strong>会议系列</strong>将相关会议归为一组（如每周站会、月度评审）。它定义了会议主题、默认参会人和业务主题。
      </p>

      <h4>查看会议系列</h4>
      <p>点击导航栏中的<strong>会议系列</strong>即可查看所有系列。</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>列</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>标题</td><td>系列名称</td></tr>
          <tr><td>分类</td><td>系列所属的业务主题</td></tr>
          <tr><td>场次数</td><td>该系列已举行的会议次数</td></tr>
          <tr><td>访问权限</td><td>显示 <Badge bg="success" className="mx-1">公开</Badge> 或 <Badge bg="warning" text="dark" className="mx-1">私有</Badge> 标签 — 私有系列仅限创建者和参会人访问</td></tr>
          <tr><td>创建日期</td><td>系列创建的日期</td></tr>
        </tbody>
      </Table>

      <h4>创建新会议系列</h4>
      <ol>
        <li>在会议系列列表页面，点击<strong>「新建系列」</strong>。</li>
        <li>填写表单：</li>
      </ol>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>字段</th><th>必填</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>标题</td><td><Badge bg="danger">是</Badge></td><td>会议系列名称（如"每周工程同步"）</td></tr>
          <tr><td>分类</td><td>否</td><td>关联的业务主题</td></tr>
          <tr><td>描述</td><td>否</td><td>会议系列的目的或范围</td></tr>
        </tbody>
      </Table>
      <ol start={3}>
        <li>点击<strong>保存</strong>。将跳转至系列详情页面。</li>
      </ol>

      <h4>管理系列详情</h4>
      <p>在系列详情页面，您可以：</p>
      <ul>
        <li><strong>编辑</strong>标题、描述、分类和可见性设置。</li>
        <li>
          <strong>管理默认参会人</strong>：添加或移除新场次自动包含的参会者。每位参会人可设为：
          <ul>
            <li><strong>必须参加</strong> — 必须出席</li>
            <li><strong>可选参加</strong> — 受邀但非必须出席</li>
          </ul>
        </li>
      </ul>

      <h4>访问控制</h4>
      <p>会议系列支持<strong>公开</strong>和<strong>私有</strong>两种可见性：</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>可见性</th><th>行为</th></tr></thead>
        <tbody>
          <tr><td><Badge bg="success">公开</Badge></td><td>任何已登录用户均可查看系列、各场次及所有关联内容（行动项、决议、备忘录）</td></tr>
          <tr><td><Badge bg="warning" text="dark">私有</Badge></td><td>仅<strong>系列创建者</strong>和<strong>已列入的参会人</strong>可访问详情页面。其他用户将看到一个<strong>锁定界面</strong>，显示系列标题并提示联系创建者</td></tr>
        </tbody>
      </Table>
      <p>在系列列表页面，您无法访问的私有系列会显示 <strong>锁定图标</strong>（🔒）而非可点击的链接。</p>

      <h4>创建会议场次</h4>
      <ol>
        <li>打开系列详情页面。</li>
        <li>在<strong>场次</strong>部分，使用日期选择器选择一个日期。</li>
        <li>点击<strong>创建场次</strong>。</li>
        <li>新场次将出现在表格中，显示：日期、状态、行动项数、决议数。</li>
      </ol>
    </>
  );
}

function SectionMeetingOccurrences() {
  return (
    <>
      <p>
        会议场次是系列中的一次具体会议。它提供了管理行动项、决议、备忘录和跟进讨论的工作空间。
      </p>

      <h4>会议详情标签页</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>标签页</th><th>用途</th></tr></thead>
        <tbody>
          <tr><td><strong>概览</strong></td><td>会议日期、系列信息、摘要和参会人列表</td></tr>
          <tr><td><strong>行动项</strong></td><td>与本次会议关联的行动项 — 创建新的或查看已有的</td></tr>
          <tr><td><strong>决议</strong></td><td>本次会议中做出的决议</td></tr>
          <tr><td><strong>备忘录</strong></td><td>自由文本记录和会议纪要</td></tr>
          <tr><td><strong>跟进</strong></td><td>审查行动项进展、添加评论、查看历史场次的讨论记录</td></tr>
        </tbody>
      </Table>

      <h4>添加备忘录</h4>
      <ol>
        <li>进入<strong>备忘录</strong>标签页。</li>
        <li>点击<strong>「添加备忘录」</strong>。</li>
        <li>输入备忘录<strong>标题</strong>和<strong>内容</strong>。</li>
        <li>点击<strong>保存</strong>。</li>
      </ol>
    </>
  );
}

function SectionActions() {
  return (
    <>
      <p>行动项是可追踪的工作任务，包含负责人（Lead）、截止日期、状态和进度追踪。</p>

      <h4>查看行动项</h4>
      <p>点击导航栏中的<strong>行动项</strong>。列表显示以下列：</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>列</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>标题</td><td>行动项标题。如果行动项关联了您不是成员的<strong>私有会议系列</strong>，标题会<strong>模糊显示</strong>并带有 🔒 标识</td></tr>
          <tr><td>负责人</td><td>行动项的责任人（Lead）</td></tr>
          <tr><td>状态</td><td>当前状态标签</td></tr>
          <tr><td>截止日期</td><td>目标完成日期</td></tr>
          <tr><td>分类</td><td>业务主题</td></tr>
        </tbody>
      </Table>

      <h4>筛选器</h4>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>筛选器</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>搜索</td><td>按标题进行全文搜索</td></tr>
          <tr><td>状态</td><td>按状态筛选（待处理、进行中、暂停、已完成、已取消）</td></tr>
          <tr><td>分类</td><td>按业务主题筛选</td></tr>
          <tr><td>系列</td><td>按会议系列筛选</td></tr>
          <tr><td>负责人</td><td>按负责人筛选 — 下拉列表仅显示<strong>您的团队成员</strong></td></tr>
          <tr><td>我负责的</td><td>切换只显示您作为负责人的行动项（默认开启）</td></tr>
          <tr><td>隐藏已关闭</td><td>切换隐藏已完成/已取消的行动项</td></tr>
        </tbody>
      </Table>

      <h4>私有系列行动项</h4>
      <p>
        关联到<strong>私有会议系列</strong>的行动项受访问控制保护。
        如果您<strong>不是</strong>该系列的创建者或参会人：
      </p>
      <ul>
        <li>行动项标题会<strong>模糊显示</strong>，并带有 🔒 锁定标识。</li>
        <li>您无法打开行动项详情页面。</li>
        <li>这确保了机密会议内容得到保护。</li>
      </ul>

      <h4>创建行动项 — 从行动项列表（独立创建）</h4>
      <ol>
        <li>在行动项列表页面点击<strong>「新建行动项」</strong>。</li>
        <li>填写表单：</li>
      </ol>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>字段</th><th>必填</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>标题</td><td><Badge bg="danger">是</Badge></td><td>行动项的简短描述</td></tr>
          <tr><td>状态</td><td>否</td><td>初始状态（默认为"待处理"）</td></tr>
          <tr><td>描述</td><td>否</td><td>详细描述</td></tr>
          <tr><td>标签</td><td>否</td><td>逗号分隔的关键词</td></tr>
          <tr><td>截止日期</td><td>否</td><td>目标完成日期</td></tr>
          <tr><td>分类</td><td>否</td><td>业务主题</td></tr>
          <tr><td>负责人</td><td>自动</td><td>自动设为创建者</td></tr>
        </tbody>
      </Table>
      <ol start={3}><li>点击<strong>保存</strong>。</li></ol>

      <h4>创建行动项 — 从会议场次</h4>
      <ol>
        <li>打开一个会议场次并进入<strong>行动项</strong>标签页。</li>
        <li>点击<strong>「新建行动项」</strong>。会议上下文会自动关联。</li>
        <li><strong>负责人</strong>字段可从参会人列表中选择。</li>
      </ol>

      <h4>编辑行动项</h4>
      <p>打开行动项详情页面并点击<strong>编辑</strong>：</p>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>字段</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>标题</td><td>编辑行动项标题</td></tr>
          <tr><td>状态</td><td>更改状态（需遵循允许的转换 — 参见"状态工作流"章节）</td></tr>
          <tr><td>优先级</td><td>设置 高 / 中 / 低</td></tr>
          <tr><td>截止日期</td><td>更新目标日期</td></tr>
          <tr><td>描述</td><td>修改详细描述</td></tr>
          <tr><td>取消原因</td><td><em>取消时必填</em> — 说明取消原因</td></tr>
          <tr><td>暂停原因</td><td><em>暂停时必填</em> — 说明暂停原因</td></tr>
        </tbody>
      </Table>
    </>
  );
}

function SectionDecisions() {
  return (
    <>
      <p>决议记录正式的决策结果，包含背景、依据和完整的修订历史。</p>

      <h4>查看决议</h4>
      <p>点击导航栏中的<strong>决议</strong>。可用筛选器：</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>筛选器</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>搜索</td><td>全文搜索</td></tr>
          <tr><td>状态</td><td>已发布或已过期</td></tr>
          <tr><td>系列</td><td>按会议系列筛选</td></tr>
          <tr><td>分类</td><td>按业务主题筛选</td></tr>
          <tr><td>创建人</td><td>按创建人筛选</td></tr>
        </tbody>
      </Table>

      <h4>创建决议</h4>
      <p>可在决议列表独立创建（→<strong>「添加决议」</strong>）或在会议场次中创建（决议标签页 → <strong>「添加决议」</strong>）。</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>字段</th><th>必填</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>标题</td><td><Badge bg="danger">是</Badge></td><td>决议的简短摘要</td></tr>
          <tr><td>状态</td><td>否</td><td>已发布（默认）或已过期</td></tr>
          <tr><td>内容</td><td>否</td><td>决议全文</td></tr>
          <tr><td>背景</td><td>否</td><td>背景信息和相关情况</td></tr>
          <tr><td>依据</td><td>否</td><td>做出此决议的原因</td></tr>
          <tr><td>标签</td><td>否</td><td>逗号分隔的关键词</td></tr>
          <tr><td>分类</td><td>否</td><td>业务主题</td></tr>
        </tbody>
      </Table>

      <h4>编辑决议</h4>
      <ol>
        <li>打开决议详情页面并点击<strong>编辑</strong>。</li>
        <li>修改所需字段并点击<strong>保存</strong>。</li>
        <li>每次编辑都会创建一个新<strong>修订版本</strong> — 完整的修订历史保留在"修订历史"部分。</li>
      </ol>

      <h4>更改决议状态</h4>
      <p><strong>已发布 → 已过期：</strong>当决议不再有效时更改。状态变更在决议详情页面操作。</p>
    </>
  );
}

function SectionFollowUp() {
  return (
    <>
      <h4>更新行动项进度</h4>
      <p>打开行动项详情页面并使用<strong>进度更新</strong>组件：</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>字段</th><th>说明</th></tr></thead>
        <tbody>
          <tr><td>完成百分比</td><td>拖动滑块从 0% 到 100% 以指示进度</td></tr>
          <tr><td>状态</td><td>从下拉菜单选择当前状态</td></tr>
          <tr><td>评论</td><td>添加关于已完成工作或下一步计划的说明</td></tr>
          <tr><td>阻碍</td><td>描述阻止进展的障碍</td></tr>
        </tbody>
      </Table>
      <p>点击<strong>更新进度</strong>。更新将记录您的姓名和时间戳。所有历史更新在反馈历史中可见。</p>

      <h4>会议中的跟进</h4>
      <p>会议场次中的<strong>跟进</strong>标签页提供行动项进展的汇总视图：</p>
      <ol>
        <li>打开一个会议场次 → <strong>跟进</strong>标签页。</li>
        <li>查看每个行动项的当前状态、完成百分比以及本次和以往场次的评论。</li>
        <li>使用每个行动项下方的文本区域添加新评论。</li>
        <li>导航到以往场次的跟进记录以查看历史讨论。</li>
      </ol>

      <h4>添加评论</h4>
      <ol>
        <li>在会议<strong>跟进</strong>标签页中，找到要评论的行动项。</li>
        <li>在标记为<em>"为 [行动项标题] 添加评论…"</em>的文本区域中输入。</li>
        <li>点击<strong>提交</strong>。</li>
        <li>评论将显示您的姓名和时间戳。</li>
      </ol>
      <p><strong>评论权限：</strong>您可以编辑或删除自己的评论。管理员可以编辑或删除任何评论。</p>
    </>
  );
}

function SectionStatusWorkflow() {
  return (
    <>
      <p>行动项遵循定义好的状态流转规则。只允许特定的状态转换：</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>当前状态</th><th>允许的下一状态</th></tr></thead>
        <tbody>
          <tr>
            <td><Badge bg="secondary">待处理</Badge></td>
            <td>
              <Badge bg="primary" className="me-1">进行中</Badge>
              <Badge bg="warning" text="dark" className="me-1">暂停</Badge>
              <Badge bg="dark">已取消</Badge>
            </td>
          </tr>
          <tr>
            <td><Badge bg="primary">进行中</Badge></td>
            <td>
              <Badge bg="warning" text="dark" className="me-1">暂停</Badge>
              <Badge bg="success" className="me-1">已完成</Badge>
              <Badge bg="dark">已取消</Badge>
            </td>
          </tr>
          <tr>
            <td><Badge bg="warning" text="dark">暂停</Badge></td>
            <td>
              <Badge bg="secondary" className="me-1">待处理</Badge>
              <Badge bg="primary" className="me-1">进行中</Badge>
              <Badge bg="dark">已取消</Badge>
            </td>
          </tr>
          <tr>
            <td><Badge bg="success">已完成</Badge></td>
            <td><em className="text-muted">终态 — 不可再更改</em></td>
          </tr>
          <tr>
            <td><Badge bg="dark">已取消</Badge></td>
            <td><em className="text-muted">终态 — 不可再更改</em></td>
          </tr>
        </tbody>
      </Table>
      <ul>
        <li>将状态更改为<strong>已取消</strong>时，必须填写<strong>取消原因</strong>。</li>
        <li>将状态更改为<strong>暂停</strong>时，必须填写<strong>暂停原因</strong>。</li>
        <li><strong>已完成</strong>和<strong>已取消</strong>是终态 — 设定后不可更改。</li>
      </ul>
    </>
  );
}

function SectionDashboards() {
  return (
    <>
      <h4>个人仪表盘</h4>
      <p>通过<strong>仪表盘 → 个人仪表盘</strong>访问。显示您作为负责人的行动项。</p>
      <Table bordered size="sm" className="mb-4">
        <thead className="table-light"><tr><th>标签页</th><th>内容</th></tr></thead>
        <tbody>
          <tr><td><strong>概览</strong></td><td>4 个关键指标卡片（总数、逾期、即将到期、已完成），逾期行动项、即将到期、近期完成和待接受的分配</td></tr>
          <tr><td><strong>按截止日期</strong></td><td>按截止日期排列的行动项</td></tr>
          <tr><td><strong>按分类</strong></td><td>按业务主题分组的行动项，每个分类有独立的关键指标摘要</td></tr>
          <tr><td><strong>甘特图</strong></td><td>行动项的时间线可视化</td></tr>
          <tr><td><strong>工作量</strong></td><td>16 周预测图表和资源工作量热力图</td></tr>
        </tbody>
      </Table>

      <h4>全局仪表盘</h4>
      <p>通过<strong>仪表盘 → 全局仪表盘</strong>访问。显示跨所有团队和业务主题的平台级关键指标和行动项统计。</p>

      <h4>团队仪表盘</h4>
      <p>通过<strong>仪表盘 → 团队仪表盘</strong>访问。仅对<strong>团队负责人</strong>和<strong>管理员</strong>开放。</p>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>标签页</th><th>内容</th></tr></thead>
        <tbody>
          <tr><td><strong>概览</strong></td><td>团队级关键指标和汇总统计</td></tr>
          <tr><td><strong>按负责人</strong></td><td>按团队成员分组的行动项</td></tr>
          <tr><td><strong>按分类</strong></td><td>按业务主题分组的行动项</td></tr>
        </tbody>
      </Table>
      <p className="mt-2 text-muted"><em>团队负责人仅可查看其所属团队的仪表盘。管理员可查看任何团队。</em></p>
    </>
  );
}

function SectionQuickRef() {
  return (
    <>
      <Table bordered size="sm">
        <thead className="table-light"><tr><th>任务</th><th>操作路径</th></tr></thead>
        <tbody>
          <tr><td>创建会议系列</td><td>会议系列 → 新建系列</td></tr>
          <tr><td>安排一次会议</td><td>系列详情 → 场次 → 选择日期 → 创建场次</td></tr>
          <tr><td>从会议创建行动项</td><td>会议详情 → 行动项标签页 → 新建行动项</td></tr>
          <tr><td>独立创建行动项</td><td>行动项 → 新建行动项</td></tr>
          <tr><td>更新行动项进度</td><td>行动项详情 → 进度更新组件</td></tr>
          <tr><td>为行动项添加评论</td><td>会议详情 → 跟进标签页 → 评论文本区域</td></tr>
          <tr><td>创建决议</td><td>决议 → 添加决议 <em>或</em> 会议详情 → 决议标签页 → 添加决议</td></tr>
          <tr><td>查看工作量</td><td>仪表盘 → 个人仪表盘 → 工作量标签页</td></tr>
          <tr><td>按负责人筛选行动项</td><td>行动项 → 负责人下拉菜单（显示您的团队成员）</td></tr>
          <tr><td>切换语言</td><td>点击导航栏的 中/英</td></tr>
          <tr><td>切换主题</td><td>点击导航栏的主题切换图标（日/月图标）</td></tr>
        </tbody>
      </Table>
    </>
  );
}

export const SECTION_COMPONENTS_ZH: Record<string, React.FC> = {
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
