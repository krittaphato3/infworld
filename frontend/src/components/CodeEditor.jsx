import Editor from '@monaco-editor/react';

function getLanguage(fileName) {
  if (!fileName) return 'plaintext';
  if (fileName.endsWith('.html')) return 'html';
  if (fileName.endsWith('.js')) return 'javascript';
  if (fileName.endsWith('.css')) return 'css';
  if (fileName.endsWith('.json')) return 'json';
  if (fileName.endsWith('.md')) return 'markdown';
  if (fileName.endsWith('.py')) return 'python';
  if (fileName.endsWith('.ts')) return 'typescript';
  if (fileName.endsWith('.jsx') || fileName.endsWith('.tsx')) return 'typescript';
  return 'plaintext';
}

export default function CodeEditor({ content, fileName }) {
  return (
    <div className="code-editor">
      <div className="code-editor-header">
        <span className="code-editor-filename">{fileName || 'Select a file'}</span>
      </div>
      <Editor
        height="100%"
        language={getLanguage(fileName)}
        value={content || ''}
        theme="vs-dark"
        options={{
          readOnly: true,
          minimap: { enabled: false },
          fontSize: 13,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          automaticLayout: true,
          padding: { top: 8 },
          renderLineHighlight: 'line',
          scrollbar: {
            verticalScrollbarSize: 8,
            horizontalScrollbarSize: 8,
          },
        }}
      />
    </div>
  );
}
