import { useMemo, useState } from "react";

import {
  THEME_COLOR_DEFAULTS,
  THEME_COLOR_META,
  THEME_OPACITY_DEFAULTS,
  THEME_OPACITY_META,
  applyShellTheme,
  deleteThemeTemplate,
  hexToRgb,
  normalizeHexColor,
  readThemeTemplates,
  rgbToHex,
  saveThemeColors,
  saveThemeTemplate,
  type ThemeColorKey,
  type ThemeColors,
  type ThemeOpacities,
  type ThemeOpacityKey,
  type ThemeTemplate,
} from "./shellTheme";

type ThemeColorEditorProps = {
  colors: ThemeColors;
  opacities: ThemeOpacities;
  onChange: (colors: ThemeColors) => void;
  onOpacitiesChange: (opacities: ThemeOpacities) => void;
  onSaved?: (message: string) => void;
};

function ColorField({
  label,
  hint,
  value,
  onChange,
}: {
  label: string;
  hint: string;
  value: string;
  onChange: (hex: string) => void;
}) {
  const rgb = useMemo(() => hexToRgb(value), [value]);
  return (
    <article className="themeColorFieldTs">
      <div className="themeColorFieldHeadTs">
        <div>
          <strong>{label}</strong>
          <span>{hint}</span>
        </div>
        <label className="themeColorSwatchTs" title={`Escolher ${label}`}>
          <input
            type="color"
            value={normalizeHexColor(value)}
            onChange={(event) => onChange(normalizeHexColor(event.target.value))}
            aria-label={`Cor ${label}`}
          />
        </label>
      </div>
      <div className="themeColorFieldControlsTs">
        <label>
          <span>Hex</span>
          <input
            value={value}
            onChange={(event) => onChange(normalizeHexColor(event.target.value, value))}
            spellCheck={false}
          />
        </label>
        <label>
          <span>R</span>
          <input
            type="number"
            min={0}
            max={255}
            value={rgb.r}
            onChange={(event) => onChange(rgbToHex(Number(event.target.value), rgb.g, rgb.b))}
          />
        </label>
        <label>
          <span>G</span>
          <input
            type="number"
            min={0}
            max={255}
            value={rgb.g}
            onChange={(event) => onChange(rgbToHex(rgb.r, Number(event.target.value), rgb.b))}
          />
        </label>
        <label>
          <span>B</span>
          <input
            type="number"
            min={0}
            max={255}
            value={rgb.b}
            onChange={(event) => onChange(rgbToHex(rgb.r, rgb.g, Number(event.target.value)))}
          />
        </label>
      </div>
    </article>
  );
}

export function ThemeColorEditor({
  colors,
  opacities,
  onChange,
  onOpacitiesChange,
  onSaved,
}: ThemeColorEditorProps) {
  const [templateName, setTemplateName] = useState("");
  const [templates, setTemplates] = useState<ThemeTemplate[]>(() => readThemeTemplates());
  const groups = useMemo(() => {
    const map = new Map<string, typeof THEME_COLOR_META>();
    for (const item of THEME_COLOR_META) {
      const list = map.get(item.group) || [];
      list.push(item);
      map.set(item.group, list);
    }
    return Array.from(map.entries());
  }, []);

  const preview = (nextColors = colors, nextOpacities = opacities) => {
    applyShellTheme(nextColors, nextOpacities);
  };

  const updateColor = (key: ThemeColorKey, hex: string) => {
    const next = { ...colors, [key]: normalizeHexColor(hex, colors[key]) };
    onChange(next);
    preview(next, opacities);
  };

  const updateOpacity = (key: ThemeOpacityKey, value: number) => {
    const meta = THEME_OPACITY_META.find((item) => item.key === key);
    const clamped = Math.min(meta?.max ?? 1, Math.max(meta?.min ?? 0, value));
    const next = { ...opacities, [key]: clamped };
    onOpacitiesChange(next);
    preview(colors, next);
  };

  const handleSaveLive = () => {
    const saved = saveThemeColors(colors, opacities);
    onChange(saved.colors);
    onOpacitiesChange(saved.opacities);
    onSaved?.("Cores e opacidades salvas neste navegador.");
  };

  const handleReset = () => {
    onChange({ ...THEME_COLOR_DEFAULTS });
    onOpacitiesChange({ ...THEME_OPACITY_DEFAULTS });
    applyShellTheme(THEME_COLOR_DEFAULTS, THEME_OPACITY_DEFAULTS);
    onSaved?.("Cores e opacidades restauradas para o padrão.");
  };

  const handleSaveTemplate = () => {
    const template = saveThemeTemplate(templateName, colors, opacities);
    setTemplates(readThemeTemplates());
    setTemplateName("");
    onSaved?.(`Template "${template.name}" salvo.`);
  };

  const handleApplyTemplate = (id: string) => {
    const template = templates.find((item) => item.id === id);
    if (!template) return;
    const saved = saveThemeColors(template.colors, template.opacities);
    onChange(saved.colors);
    onOpacitiesChange(saved.opacities);
    onSaved?.(`Template "${template.name}" aplicado.`);
  };

  const handleDeleteTemplate = (id: string) => {
    deleteThemeTemplate(id);
    setTemplates(readThemeTemplates());
    onSaved?.("Template removido.");
  };

  return (
    <section className="settingsPanel themeColorEditorTs" aria-labelledby="theme-colors-title">
      <div className="settingsPanelHead">
        <div>
          <span className="sectionTag">Cores</span>
          <strong id="theme-colors-title">Paleta da interface</strong>
        </div>
        <div className="settingsAppearanceActions">
          <button className="ghostButton miniActionButton" type="button" onClick={handleReset}>
            Restaurar padrão
          </button>
          <button className="primaryButton miniActionButton" type="button" onClick={handleSaveLive}>
            Salvar cores
          </button>
        </div>
      </div>
      <p className="settingsAppearanceHint">
        Controle cores e opacidade de botões, pílulas da lista (marca/categoria) e fundo da tabela.
        O preview aplica na hora; salve para manter ou grave um template.
      </p>

      {groups.map(([group, items]) => (
        <div key={group} className="themeColorGroupTs">
          <h4>{group}</h4>
          <div className="themeColorGridTs">
            {items.map((item) => (
              <ColorField
                key={item.key}
                label={item.label}
                hint={item.hint}
                value={colors[item.key]}
                onChange={(hex) => updateColor(item.key, hex)}
              />
            ))}
          </div>
        </div>
      ))}

      <div className="themeColorGroupTs">
        <h4>Opacidade</h4>
        <div className="themeOpacityGridTs">
          {THEME_OPACITY_META.map((item) => (
            <label key={item.key} className="themeOpacityFieldTs">
              <span>
                <strong>{item.label}</strong>
                <em>{item.hint}</em>
              </span>
              <div>
                <input
                  type="range"
                  min={item.min}
                  max={item.max}
                  step={0.01}
                  value={opacities[item.key]}
                  onChange={(event) => updateOpacity(item.key, Number(event.target.value))}
                />
                <strong>{Math.round(opacities[item.key] * 100)}%</strong>
              </div>
            </label>
          ))}
        </div>
      </div>

      <div className="themeTemplatePanelTs">
        <div className="themeTemplateSaveTs">
          <label>
            <span>Salvar como template</span>
            <input
              value={templateName}
              onChange={(event) => setTemplateName(event.target.value)}
              placeholder="Ex.: Noite azul, Operação ouro..."
            />
          </label>
          <button className="ghostButton miniActionButton" type="button" onClick={handleSaveTemplate} disabled={!templateName.trim()}>
            Salvar template
          </button>
        </div>
        {templates.length ? (
          <ul className="themeTemplateListTs">
            {templates.map((template) => (
              <li key={template.id}>
                <div>
                  <strong>{template.name}</strong>
                  <span>{new Date(template.savedAt).toLocaleString("pt-BR")}</span>
                  <span className="themeTemplateSwatchesTs" aria-hidden="true">
                    {(["accent", "primary", "badgeBrand", "badgeCategory"] as ThemeColorKey[]).map((key) => (
                      <i key={key} style={{ background: template.colors[key] }} />
                    ))}
                  </span>
                </div>
                <div>
                  <button className="ghostButton miniActionButton" type="button" onClick={() => handleApplyTemplate(template.id)}>
                    Aplicar
                  </button>
                  {template.id.startsWith("builtin-") ? null : (
                    <button className="ghostButton miniActionButton" type="button" onClick={() => handleDeleteTemplate(template.id)}>
                      Apagar
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="settingsAppearanceHint">Nenhum template salvo ainda.</p>
        )}
      </div>
    </section>
  );
}
