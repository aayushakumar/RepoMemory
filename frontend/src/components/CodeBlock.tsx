import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

interface Props {
  code: string;
  language: string;
}

const LANG_MAP: Record<string, string> = {
  py: "python",
  js: "javascript",
  jsx: "jsx",
  ts: "typescript",
  tsx: "tsx",
};

export default function CodeBlock({ code, language }: Props) {
  const lang = LANG_MAP[language] ?? language;

  return (
    <div className="rounded-md overflow-hidden border border-border text-[13px]">
      <SyntaxHighlighter
        language={lang}
        style={vscDarkPlus}
        customStyle={{
          margin: 0,
          padding: "12px 16px",
          background: "#0d0d18",
          fontSize: "13px",
          lineHeight: "1.5",
        }}
        wrapLongLines
      >
        {code}
      </SyntaxHighlighter>
    </div>
  );
}
