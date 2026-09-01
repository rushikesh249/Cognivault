import React from 'react';
import { Badge } from '../common/Badge';
import { IconCode, IconDatabase, IconEye, IconFileText, IconLock } from '../common/Icons';

export const ToolsView: React.FC = () => {
  const tools = [
    {
      name: 'ChromaDB Local Vector Retriever',
      category: 'Knowledge / RAG',
      sandbox: 'Air-Gapped',
      permission: 'Read Only',
      network: 'Isolated',
      status: 'Active',
      icon: <IconDatabase size={17} color="#4338ca" />,
    },
    {
      name: 'Tesseract / EasyOCR Engine',
      category: 'Document Extraction',
      sandbox: 'Host / Container',
      permission: 'Read File',
      network: 'Isolated',
      status: 'Active',
      icon: <IconFileText size={17} color="#4338ca" />,
    },
    {
      name: 'Docker Python Sandbox Executor',
      category: 'Code Execution',
      sandbox: 'Isolated Container (cgroups)',
      permission: 'Execute Code',
      network: 'Network Disabled',
      status: 'Active',
      icon: <IconCode size={17} color="#15803d" />,
    },
    {
      name: 'Local VLM Visual Diagnostic Engine',
      category: 'Multimodal Vision',
      sandbox: 'GPU Acceleration',
      permission: 'Read Image',
      network: 'Isolated',
      status: 'Active',
      icon: <IconEye size={17} color="#4338ca" />,
    },
    {
      name: 'Deliverable Document Synthesizer (DOCX/XLSX/PPTX)',
      category: 'Artifact Generation',
      sandbox: 'Host Memory',
      permission: 'Write Artifact',
      network: 'Isolated',
      status: 'Active',
      icon: <IconFileText size={17} color="#b45309" />,
    },
  ];

  return (
    <div className="cv-view-layout">
      <div className="cv-section-header-row">
        <div>
          <h2 className="cv-section-title">Sandboxed Tool Inventory</h2>
          <p className="cv-section-subtitle">
            Local tool executors and isolation policies authorized for sovereign autonomous agents.
          </p>
        </div>
      </div>

      <div className="cv-card cv-table-card">
        <table className="cv-data-table">
          <thead>
            <tr>
              <th>TOOL</th>
              <th>CATEGORY</th>
              <th>SANDBOX BOUNDARY</th>
              <th>PERMISSIONS</th>
              <th>NETWORK POLICY</th>
              <th style={{ textAlign: 'right' }}>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {tools.map((t) => (
              <tr key={t.name}>
                <td>
                  <div className="cv-subsystem-name">
                    {t.icon}
                    <strong style={{ color: '#111827' }}>{t.name}</strong>
                  </div>
                </td>
                <td>
                  <span className="cv-badge-isolation">{t.category}</span>
                </td>
                <td>
                  <span className="cv-mono-text">{t.sandbox}</span>
                </td>
                <td>
                  <span className="cv-mono-text">{t.permission}</span>
                </td>
                <td>
                  <span className="cv-text-green" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                    <IconLock size={14} /> {t.network}
                  </span>
                </td>
                <td style={{ textAlign: 'right' }}>
                  <Badge variant="success">ACTIVE</Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
