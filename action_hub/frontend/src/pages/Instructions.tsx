import React, { useState } from "react";
import { Nav } from "react-bootstrap";
import { t, getCurrentLanguage } from "../lib/i18n";
import { SECTION_LABELS_EN, SECTION_COMPONENTS_EN } from "./InstructionsEn";
import { SECTION_LABELS_ZH, SECTION_COMPONENTS_ZH } from "./InstructionsZh";

const SECTIONS = [
  "overview",
  "meetingSeries",
  "meetingOccurrences",
  "actions",
  "decisions",
  "followUp",
  "statusWorkflow",
  "dashboards",
  "quickRef",
] as const;

type Section = typeof SECTIONS[number];

export default function Instructions() {
  const [active, setActive] = useState<Section>("overview");
  const lang = getCurrentLanguage();
  const labels = lang === "zh" ? SECTION_LABELS_ZH : SECTION_LABELS_EN;
  const components = lang === "zh" ? SECTION_COMPONENTS_ZH : SECTION_COMPONENTS_EN;
  const SectionContent = components[active];

  return (
    <div className="container-fluid py-4">
      <h2 className="mb-1">{t("instructions.sop_title", "ActionHub Instruction Manual")}</h2>
      <p className="text-muted mb-4">{t("instructions.sop_desc", "Step-by-step guide for meetings, actions, and decisions.")}</p>

      <div className="row">
        {/* Sidebar nav */}
        <div className="col-12 col-md-3 col-lg-2 mb-3 mb-md-0">
          <Nav className="flex-column" variant="pills">
            {SECTIONS.map((s) => (
              <Nav.Link
                key={s}
                active={active === s}
                onClick={() => setActive(s)}
                style={{ cursor: "pointer", fontSize: "0.9rem", paddingTop: 6, paddingBottom: 6 }}
              >
                {labels[s]}
              </Nav.Link>
            ))}
          </Nav>
        </div>

        {/* Content panel */}
        <div className="col-12 col-md-9 col-lg-10">
          <div className="p-4 rounded border bg-white">
            <h3 className="mb-3">{labels[active]}</h3>
            <SectionContent />
          </div>
        </div>
      </div>
    </div>
  );
}
