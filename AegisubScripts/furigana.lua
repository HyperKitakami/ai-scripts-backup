-- furigana.lua  v4.0  (Aegisub 3.x / Lua 5.1)
-- 将 {汉字/假名} 标记转换为 ASS 注音行
--
-- 输入格式：{強/つよ}く{思/おも}い{巡/めぐ}らせ
-- 选中行后执行：自动化 → 生成振り仮名

script_name        = "生成振り仮名"
script_description = "将 {汉字/假名} 标记转换为 ASS 注音行"
script_version     = "4.0"
script_author      = "furigana-tool"

local CFG = {
    ruby_scale     = 0.40,
    ruby_gap_ratio = 0.10,
    ruby_layer     = 1,
}

-- ──────────────────────────────────────────
-- UTF-8（Lua 5.1，无位运算）
-- ──────────────────────────────────────────
local function utf8_charlen(b)
    if b < 128 then return 1
    elseif b < 224 then return 2
    elseif b < 240 then return 3
    else return 4
    end
end

local function utf8_split(s)
    local chars = {}
    local i = 1
    while i <= #s do
        local n = utf8_charlen(s:byte(i))
        table.insert(chars, s:sub(i, i + n - 1))
        i = i + n
    end
    return chars
end

-- ──────────────────────────────────────────
-- 字宽测量
-- ──────────────────────────────────────────
local function estimate_width(text, fontsize)
    local w = 0
    for _, c in ipairs(utf8_split(text)) do
        if c:byte(1) >= 128 then
            w = w + fontsize
        else
            w = w + fontsize * 0.55
        end
    end
    return w
end

local function measure_width(style, text, fontsize_override)
    if text == "" then return 0 end
    local fs_orig = style.fontsize
    if fontsize_override then
        style.fontsize = math.floor(fontsize_override)
    end
    local w
    if style.fontname and style.fontname ~= "" then
        local ok, tw = pcall(function()
            local w2, _ = aegisub.text_extents(style, text)
            return w2
        end)
        if ok and tw then
            w = tw
        else
            w = estimate_width(text, style.fontsize)
        end
    else
        w = estimate_width(text, style.fontsize)
    end
    style.fontsize = fs_orig
    return w
end

-- ──────────────────────────────────────────
-- ASS 工具
-- ──────────────────────────────────────────
local function get_play_res(subs)
    local rx, ry = 640, 480
    for _, line in ipairs(subs) do
        if line.class == "info" then
            if line.key == "PlayResX" then rx = tonumber(line.value) or rx end
            if line.key == "PlayResY" then ry = tonumber(line.value) or ry end
        end
    end
    return rx, ry
end

local function find_style(subs, name)
    for _, line in ipairs(subs) do
        if line.class == "style" and line.name == name then
            return line
        end
    end
    return nil
end

local function strip_tags(s)
    return (s:gsub("{[^}]*}", ""))
end

local function extract_pos(text)
    local x, y = text:match("\\pos%(([%d%.%-]+)%s*,%s*([%d%.%-]+)%)")
    if x then return tonumber(x), tonumber(y) end
    return nil, nil
end

local function extract_an(text)
    local an = text:match("\\an(%d)")
    return an and tonumber(an) or nil
end

local function left_edge(pos_x, text_w, an)
    local h = (an - 1) % 3
    if h == 0 then return pos_x
    elseif h == 1 then return pos_x - text_w / 2
    else return pos_x - text_w
    end
end

local function get_text_top(pos_y, fontsize, an)
    local v = math.floor((an - 1) / 3)
    if v == 0 then return pos_y - fontsize
    elseif v == 1 then return pos_y - fontsize / 2
    else return pos_y
    end
end

local function pos_from_margin(line, style, an, rx, ry)
    local ml = (line.margin_l ~= 0) and line.margin_l or (style and style.margin_l or 15)
    local mr = (line.margin_r ~= 0) and line.margin_r or (style and style.margin_r or 15)
    local mv = (line.margin_v ~= 0) and line.margin_v or (style and style.margin_v or 5)
    local h = (an - 1) % 3
    local v = math.floor((an - 1) / 3)
    local px = (h == 0) and ml or (h == 1) and (rx / 2) or (rx - mr)
    local py = (v == 0) and (ry - mv) or (v == 1) and (ry / 2) or mv
    return px, py
end

-- ──────────────────────────────────────────
-- 解析注音标记
-- ──────────────────────────────────────────
local function parse_tokens(raw)
    local tokens = {}

    local function append_plain(s)
        if s == "" then return end
        local n = #tokens
        if n > 0 and tokens[n].type == "plain" then
            tokens[n].text = tokens[n].text .. s
        else
            table.insert(tokens, { type = "plain", text = s })
        end
    end

    local i = 1
    while i <= #raw do
        if raw:sub(i, i) ~= "{" then
            local n = utf8_charlen(raw:byte(i))
            append_plain(raw:sub(i, i + n - 1))
            i = i + n
        else
            local e = raw:find("}", i, true)
            if not e then
                append_plain(raw:sub(i))
                i = #raw + 1
            else
                local inner = raw:sub(i + 1, e - 1)
                if inner:sub(1, 1) == "\\" then
                    append_plain(raw:sub(i, e))
                else
                    local slash = inner:find("/", 1, true)
                    if slash then
                        table.insert(tokens, {
                            type = "ruby",
                            base = inner:sub(1, slash - 1),
                            ruby = inner:sub(slash + 1),
                        })
                    else
                        append_plain(raw:sub(i, e))
                    end
                end
                i = e + 1
            end
        end
    end

    return tokens
end

-- ──────────────────────────────────────────
-- 构造注音 dialogue 行
-- 从现有 line 复制，只修改必要字段
-- 避免手动设置 extra/section 等旧版不支持的字段
-- ──────────────────────────────────────────
local function make_ruby_line(template_line, tag_and_text)
    -- 深拷贝 template_line
    local rl = {}
    for k, v in pairs(template_line) do
        rl[k] = v
    end
    rl.layer   = CFG.ruby_layer
    rl.actor   = ""
    rl.margin_l = 0
    rl.margin_r = 0
    rl.margin_v = 0
    rl.effect  = ""
    rl.text    = tag_and_text
    rl.comment = false
    return rl
end

-- ──────────────────────────────────────────
-- 主处理
-- ──────────────────────────────────────────
local function process(subs, sel)
    local play_res_x, play_res_y = get_play_res(subs)
    local ops = {}

    for _, si in ipairs(sel) do
        local line = subs[si]
        if line.class == "dialogue" then
            local raw    = line.text
            local tokens = parse_tokens(raw)

            local has_ruby = false
            for _, tok in ipairs(tokens) do
                if tok.type == "ruby" then has_ruby = true; break end
            end

            if has_ruby then
                local style   = find_style(subs, line.style)
                local main_fs = style and style.fontsize or 70
                local ruby_fs = main_fs * CFG.ruby_scale
                local an      = extract_an(raw) or (style and style.alignment) or 1

                -- 干净主文本
                local parts = {}
                for _, tok in ipairs(tokens) do
                    if tok.type == "plain" then
                        table.insert(parts, tok.text)
                    else
                        table.insert(parts, tok.base)
                    end
                end
                local clean_text = table.concat(parts)

                -- 定位
                local pos_x, pos_y = extract_pos(raw)
                if not pos_x then
                    pos_x, pos_y = pos_from_margin(line, style, an, play_res_x, play_res_y)
                end

                local main_w  = measure_width(style, strip_tags(clean_text), main_fs)
                local lx      = left_edge(pos_x, main_w, an)
                local top_y   = get_text_top(pos_y, main_fs, an)
                local ruby_y  = top_y - main_fs * CFG.ruby_gap_ratio - ruby_fs * 0.5

                -- 生成注音行
                local ruby_lines = {}
                local cursor_x   = lx
                local scale_pct  = math.floor(CFG.ruby_scale * 100)

                for _, tok in ipairs(tokens) do
                    local body  = strip_tags(tok.type == "plain" and tok.text or tok.base)
                    local tok_w = measure_width(style, body, main_fs)

                    if tok.type == "ruby" then
                        local ruby_w = measure_width(style, tok.ruby, ruby_fs)
                        local rx     = cursor_x + (tok_w - ruby_w) / 2
                        local tag    = string.format(
                            "{\\an7\\pos(%.0f,%.0f)\\fscx%d\\fscy%d}",
                            rx, ruby_y, scale_pct, scale_pct
                        )
                        table.insert(ruby_lines, make_ruby_line(line, tag .. tok.ruby))
                    end

                    cursor_x = cursor_x + tok_w
                end

                table.insert(ops, { si = si, clean_text = clean_text, ruby_lines = ruby_lines })
            end
        end
    end

    if #ops == 0 then
        aegisub.log("未找到带注音标记的行。\n格式示例：{強/つよ}く{思/おも}い\n")
        return
    end

    -- 倒序插入，避免行索引偏移
    for i = #ops, 1, -1 do
        local op = ops[i]

        local line = subs[op.si]
        line.text  = op.clean_text
        subs[op.si] = line

        for j = #op.ruby_lines, 1, -1 do
            subs.insert(op.si + 1, op.ruby_lines[j])
        end
    end

    aegisub.set_undo_point(script_name)
    aegisub.log(string.format("完成：处理了 %d 行。\n", #ops))
end

aegisub.register_macro(script_name, script_description, process)
