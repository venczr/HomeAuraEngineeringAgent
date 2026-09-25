using System.Text;

namespace HomeAura.NativeEditor;

public sealed class MainForm : Form
{
    private readonly EditorCanvas _canvas = new();
    private readonly ListView _analysis = new();
    private readonly ToolStripStatusLabel _status = new("Готово");
    private readonly ToolStripButton _select = new("Выбор");
    private readonly ToolStripButton _wall = new("Стена");
    private readonly ToolStripButton _window = new("Окно");
    private readonly ToolStripButton _collector = new("Коллектор");
    private readonly ToolStripButton _circuit = new("Контур");
    private readonly ToolStripComboBox _wallType = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 145 };
    private readonly ToolStripComboBox _wallThickness = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 95 };
    private readonly ToolStripComboBox _gridSpacing = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 92 };
    private readonly ToolStripComboBox _activeFloor = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 150 };
    private readonly List<string?> _activeFloorIds = [];
    private readonly ToolStripComboBox _circuitLayer = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 145 };
    private readonly ToolStripButton _orthogonal = new("Ортогонально") { CheckOnClick = true, Checked = true };
    private readonly ComboBox _label = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 160 };
    private readonly TextBox _notes = new() { Multiline = true, Dock = DockStyle.Fill, ScrollBars = ScrollBars.Vertical };
    private string? _currentPath;
    private bool _metadataSync;

    public MainForm(string? startupProjectPath = null)
    {
        Text = "HomeAura Manual Routing Editor";
        Width = 1500; Height = 930; MinimumSize = new Size(1050, 650);
        BackColor = Color.FromArgb(7, 16, 22); ForeColor = Color.FromArgb(235, 246, 249);
        KeyPreview = true;

        var toolbar = BuildToolbar();
        var rightPanel = BuildRightPanel();
        var split = new SplitContainer { Dock = DockStyle.Fill, FixedPanel = FixedPanel.Panel2, BackColor = Color.FromArgb(34, 52, 62) };
        split.Panel1.Controls.Add(_canvas); split.Panel2.Controls.Add(rightPanel);
        var statusBar = new StatusStrip { BackColor = Color.FromArgb(10, 25, 32), ForeColor = ForeColor }; statusBar.Items.Add(_status);
        Controls.Add(split); Controls.Add(toolbar); Controls.Add(statusBar);
        Shown += (_, _) => { split.SplitterDistance = Math.Max(600, split.Width - 340); split.Panel2MinSize = 300; };

        _canvas.ProjectChanged += (_, _) => RefreshAnalysis();
        _canvas.StatusChanged += (_, message) => _status.Text = message;
        _label.Items.AddRange(["DRAFT — черновик", "ACCEPTED — правильный пример", "REJECTED — неправильный пример"]);
        _label.SelectedIndex = 0;
        _wallType.Items.AddRange(["Внутренняя стена", "Наружная стена"]); _wallType.SelectedIndex = 0;
        _wallType.SelectedIndexChanged += (_, _) => _canvas.NewWallType = _wallType.SelectedIndex == 1 ? "EXTERIOR" : "INTERIOR";
        _wallThickness.Items.AddRange(["100 мм", "150 мм", "200 мм", "250 мм", "300 мм", "400 мм"]); _wallThickness.SelectedIndex = 2;
        _wallThickness.SelectedIndexChanged += (_, _) => _canvas.NewWallThicknessMm = int.Parse(_wallThickness.Text.Split(' ')[0]);
        _gridSpacing.Items.AddRange(["Сетка 50", "Сетка 100", "Сетка 200"]); _gridSpacing.SelectedIndex = 1;
        _gridSpacing.SelectedIndexChanged += (_, _) =>
        {
            if (_metadataSync) return;
            var requested = int.Parse(_gridSpacing.Text.Split(' ')[1]);
            if (!_canvas.TrySetGridSpacing(requested)) SyncProjectControls();
        };
        _activeFloor.SelectedIndexChanged += (_, _) =>
        {
            if (_metadataSync || _activeFloor.SelectedIndex < 0 || _activeFloor.SelectedIndex >= _activeFloorIds.Count) return;
            _canvas.ActiveFloorId = _activeFloorIds[_activeFloor.SelectedIndex];
            _canvas.FitToProject();
            _status.Text = _canvas.ActiveFloorId is null ? "Показаны все этажи" : $"Активный этаж: {_canvas.ActiveFloorId}";
        };
        _circuitLayer.Items.AddRange(["Тёплый пол", "Сервис 2 этажа", "Подъём", "Подводка этажа"]); _circuitLayer.SelectedIndex = 0;
        _circuitLayer.SelectedIndexChanged += (_, _) =>
        {
            (_canvas.NewCircuitRoutingLayer, _canvas.NewCircuitSystemRole) = _circuitLayer.SelectedIndex switch
            {
                1 => ("LOWER_SERVICE_LAYER", "INTERFLOOR_SERVICE_LEG"),
                2 => ("VERTICAL_RISER_PROJECTION", "RISER_PROJECTION"),
                3 => ("LOWER_SERVICE_LAYER", "FLOOR_SERVICE_LEG"),
                _ => ("HEATING_PLANE", "FLOOR_HEATING_LOOP")
            };
        };
        _orthogonal.CheckedChanged += (_, _) => _canvas.OrthogonalMode = _orthogonal.Checked;
        _label.SelectedIndexChanged += (_, _) => { if (_metadataSync) return; _canvas.Project.Training.Label = _label.SelectedIndex switch { 1 => "ACCEPTED", 2 => "REJECTED", _ => "DRAFT" }; _canvas.MarkDirty(); };
        _notes.TextChanged += (_, _) => { if (_metadataSync) return; _canvas.Project.Training.Notes = _notes.Text; _canvas.MarkDirty(); };
        _canvas.DirtyChanged += (_, _) => UpdateTitle();
        _canvas.NewProject(HomeAuraProject.CreateBlank());
        SyncProjectControls();
        SetTool(EditorTool.Select);
        if (!string.IsNullOrWhiteSpace(startupProjectPath))
            Shown += (_, _) => LoadProjectFile(startupProjectPath);
    }

    private ToolStrip BuildToolbar()
    {
        var strip = new ToolStrip { Dock = DockStyle.Top, GripStyle = ToolStripGripStyle.Hidden, Height = 46, BackColor = Color.FromArgb(10, 25, 32), ForeColor = ForeColor, Padding = new Padding(8, 5, 8, 5) };
        ToolStripButton Button(string text, EventHandler action) { var button = new ToolStripButton(text) { DisplayStyle = ToolStripItemDisplayStyle.Text, AutoSize = true }; button.Click += action; return button; }
        strip.Items.Add(Button("Новый", (_, _) => NewProject()));
        strip.Items.Add(Button("Открыть", (_, _) => OpenProject()));
        strip.Items.Add(Button("Сохранить", (_, _) => SaveProject(false)));
        strip.Items.Add(Button("Сохранить как", (_, _) => SaveProject(true)));
        strip.Items.Add(Button("Экспорт PNG", (_, _) => ExportPng()));
        strip.Items.Add(new ToolStripSeparator());
        strip.Items.Add(Button("↶ Отмена", (_, _) => _canvas.Undo()));
        strip.Items.Add(Button("↷ Повтор", (_, _) => _canvas.Redo()));
        strip.Items.Add(Button("Вписать", (_, _) => _canvas.FitToProject()));
        strip.Items.Add(Button("Удалить", (_, _) => _canvas.DeleteSelection()));
        strip.Items.Add(Button("↻ Коллектор 90° (R)", (_, _) => _canvas.RotateSelectedCollector()));
        strip.Items.Add(new ToolStripSeparator());
        foreach (var pair in new[] { (_select, EditorTool.Select), (_wall, EditorTool.Wall), (_window, EditorTool.Window), (_collector, EditorTool.Collector), (_circuit, EditorTool.Circuit) })
        { pair.Item1.CheckOnClick = true; pair.Item1.Click += (_, _) => SetTool(pair.Item2); strip.Items.Add(pair.Item1); }
        strip.Items.Add(_wallType);
        strip.Items.Add(_wallThickness);
        strip.Items.Add(_gridSpacing);
        strip.Items.Add(_activeFloor);
        strip.Items.Add(_circuitLayer);
        strip.Items.Add(_orthogonal);
        var view = new ToolStripDropDownButton("Вид");
        void Toggle(string text, Func<bool> read, Action<bool> write)
        {
            var item = new ToolStripMenuItem(text) { Checked = read(), CheckOnClick = true };
            item.CheckedChanged += (_, _) => { write(item.Checked); _canvas.Invalidate(); };
            view.DropDownItems.Add(item);
        }
        Toggle("Сетка", () => _canvas.ShowGrid, value => _canvas.ShowGrid = value);
        Toggle("Контуры пола", () => _canvas.ShowHeatingCircuits, value => _canvas.ShowHeatingCircuits = value);
        Toggle("Межэтажные трассы", () => _canvas.ShowServiceCircuits, value => _canvas.ShowServiceCircuits = value);
        Toggle("3D-переходы и STACK", () => _canvas.Show3DRouteMarkers, value => _canvas.Show3DRouteMarkers = value);
        Toggle("Инженерные нарушения", () => _canvas.ShowEngineeringDiagnostics, value => _canvas.ShowEngineeringDiagnostics = value);
        Toggle("Подписи коллекторов", () => _canvas.ShowCollectorLabels, value => _canvas.ShowCollectorLabels = value);
        strip.Items.Add(view);
        strip.Items.Add(Button("Завершить линию (Enter)", (_, _) => _canvas.FinishCurrent()));
        return strip;
    }

    private Control BuildRightPanel()
    {
        var panel = new TableLayoutPanel { Dock = DockStyle.Fill, RowCount = 6, ColumnCount = 1, BackColor = Color.FromArgb(11, 22, 29), Padding = new Padding(14) };
        panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 34)); panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 34)); panel.RowStyles.Add(new RowStyle(SizeType.Percent, 55)); panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 32)); panel.RowStyles.Add(new RowStyle(SizeType.Percent, 45)); panel.RowStyles.Add(new RowStyle(SizeType.Absolute, 44));
        panel.Controls.Add(Label("АНАЛИЗ РУЧНОГО ЧЕРТЕЖА"), 0, 0);
        panel.Controls.Add(_label, 0, 1);
        _analysis.Dock = DockStyle.Fill; _analysis.View = View.Details; _analysis.FullRowSelect = true; _analysis.GridLines = true; _analysis.ShowItemToolTips = true; _analysis.BackColor = Color.FromArgb(9, 20, 26); _analysis.ForeColor = ForeColor;
        _analysis.Columns.Add("Контур", 76); _analysis.Columns.Add("Длина", 62); _analysis.Columns.Add("Колл.", 50); _analysis.Columns.Add("×", 25); _analysis.Columns.Add("Меж.", 34); _analysis.Columns.Add("Тело/стена", 68); _analysis.Columns.Add("Шаг", 72); _analysis.Columns.Add("R", 38); _analysis.Columns.Add("3×100", 50); _analysis.Columns.Add("Итог", 46);
        panel.Controls.Add(_analysis, 0, 2);
        panel.Controls.Add(Label("ЗАМЕТКИ К ОБУЧАЮЩЕМУ ПРИМЕРУ"), 0, 3); panel.Controls.Add(_notes, 0, 4);
        var hint = new Label { Text = "ЛКМ — точки/выбор · R — повернуть выбранный коллектор · Delete — удалить · ПКМ/средняя — панорама · колесо — масштаб · Enter — завершить трубу", Dock = DockStyle.Fill, ForeColor = Color.FromArgb(120, 149, 160), Font = new Font("Segoe UI", 8), Padding = new Padding(0, 7, 0, 0) };
        panel.Controls.Add(hint, 0, 5); return panel;
    }

    private static Label Label(string text) => new() { Text = text, Dock = DockStyle.Fill, ForeColor = Color.FromArgb(103, 232, 249), Font = new Font("Segoe UI Semibold", 10), TextAlign = ContentAlignment.MiddleLeft };

    private void SetTool(EditorTool tool)
    {
        _canvas.Tool = tool;
        foreach (var button in new[] { _select, _wall, _window, _collector, _circuit }) button.Checked = false;
        (tool switch { EditorTool.Wall => _wall, EditorTool.Window => _window, EditorTool.Collector => _collector, EditorTool.Circuit => _circuit, _ => _select }).Checked = true;
    }

    private void RefreshAnalysis()
    {
        _analysis.BeginUpdate(); _analysis.Items.Clear();
        foreach (var circuit in _canvas.Project.Circuits)
        {
            var item = CircuitAnalyzer.Analyze(_canvas.Project, circuit);
            var row = new ListViewItem(item.Name);
            row.SubItems.Add($"{item.LengthMm / 1000:0.0} м"); row.SubItems.Add(item.StartAtCollector && item.EndAtCollector ? "оба" : item.StartAtCollector || item.EndAtCollector ? "один" : "нет"); row.SubItems.Add(item.SelfSurfaceClearanceViolations == 0 ? item.SelfIntersections.ToString() : $"{item.SelfIntersections}/{item.SelfSurfaceClearanceViolations}"); row.SubItems.Add(item.InterCircuitSurfaceClearanceViolations == 0 ? item.InterCircuitIntersections.ToString() : $"{item.InterCircuitIntersections}/{item.InterCircuitSurfaceClearanceViolations}"); row.SubItems.Add(item.HeatingBodyPointCount == 0 ? "—" : item.HeatingBodyPlacementPass ? "OK" : $"×{item.HeatingBodyWallIntrusions}"); row.SubItems.Add($"100:{item.Spacing100Samples} 200:{item.Spacing200Samples}");
            var radiusReworkCount = item.BendRadiusViolationCount + item.VerticalTransitions.Count(transition => !transition.RadiusPass);
            row.SubItems.Add(item.BendRadiusFeasible ? "OK" : $"×{radiusReworkCount}");
            row.SubItems.Add(item.Exterior3x100UsefulSpanApplicable
                ? item.Exterior3x100UsefulSpanPass ? "OK*" : $"×{item.ExteriorWallBandUsefulSpanDetails.Count(detail => !detail.UsefulSpanPass)}*"
                : !item.Exterior3x100Applicable ? "—" : item.Exterior3x100Pass ? "OK" : $"×{item.ExteriorWallBandCoverageDetails.Count(detail => !detail.CoveragePass)}");
            row.SubItems.Add(item.DesignPass ? "PASS" : "ПРОВ.");
            row.ToolTipText = BuildDiagnosticsTooltip(item);
            row.ForeColor = item.DesignPass ? Color.FromArgb(94, 234, 212) : Color.FromArgb(253, 164, 175); _analysis.Items.Add(row);
        }
        _analysis.EndUpdate();
    }

    private static string BuildDiagnosticsTooltip(CircuitAnalysis analysis)
    {
        var lines = new List<string>();
        foreach (var bend in analysis.BendRadiusViolations)
            lines.Add($"R80: сегмент {bend.SegmentIndex}, {bend.AvailableLengthMm:0.#}/{bend.RequiredTangentLengthMm} мм");
        foreach (var transition in analysis.VerticalTransitions.Where(item => !item.MaterializedPass))
            lines.Add($"3D {transition.Kind}: сегмент {transition.CircuitSegmentIndex}, геометрия {(transition.GeometryPass ? "OK" : "REWORK")}, R{transition.RadiusMm:0.#}");
        if (analysis.UnmaterializedElevationChangeCount > 0)
            lines.Add($"3D: {analysis.UnmaterializedElevationChangeCount} перепад(а) Z без S-перехода");
        foreach (var clearance in analysis.InterCircuitSurfaceClearanceViolationDetails.Take(5))
            lines.Add($"Зазор: сегмент {clearance.CircuitSegmentIndex}/{clearance.OtherCircuitId}:{clearance.OtherCircuitSegmentIndex}, поверхность {clearance.SurfaceClearanceMm:0.#}/{clearance.RequiredSurfaceClearanceMm:0.#} мм");
        foreach (var intrusion in analysis.HeatingBodyWallIntrusionDetails)
            lines.Add($"Стена {intrusion.WallId}: сегмент тела {intrusion.HeatingBodySegmentIndex}, заход {intrusion.IntrusionDepthMm:0.#} мм");
        foreach (var lane in analysis.ExteriorWallBandUsefulSpanDetails.Where(item => !item.UsefulSpanPass))
            lines.Add($"3×100 useful {lane.WallId} L{lane.LaneIndex}: {lane.CoveragePercent:0.#}%, окно {lane.WindowCoveragePercent:0.#}%");
        var usefulKeys = analysis.ExteriorWallBandUsefulSpanDetails
            .Select(item => (item.RoomId, item.WallId, item.LaneIndex))
            .ToHashSet();
        foreach (var lane in analysis.ExteriorWallBandCoverageDetails.Where(item => !item.CoveragePass))
            lines.Add(usefulKeys.Contains((lane.RoomId, lane.WallId, lane.LaneIndex))
                ? $"3×100 raw {lane.WallId} L{lane.LaneIndex}: {lane.CoveragePercent:0.#}% (useful-span рассчитан отдельно)"
                : $"3×100 {lane.WallId} L{lane.LaneIndex}: {lane.CoveragePercent:0.#}%, окно {lane.WindowCoveragePercent:0.#}%");
        return lines.Count == 0 ? "Инженерных нарушений не обнаружено" : string.Join(Environment.NewLine, lines);
    }

    private void NewProject()
    {
        if (!ConfirmDiscardOrSave()) return;
        using var dialog = new NewProjectDialog();
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        _currentPath = null; _canvas.NewProject(new HomeAuraProject { CanvasWidthMm = dialog.WidthMm, CanvasHeightMm = dialog.HeightMm });
        SyncProjectControls();
        _metadataSync = true; _label.SelectedIndex = 0; _notes.Clear(); _metadataSync = false; _canvas.MarkClean(); UpdateTitle();
    }

    private void OpenProject()
    {
        if (!ConfirmDiscardOrSave()) return;
        using var dialog = new OpenFileDialog { Filter = "HomeAura project (*.homeaura.json)|*.homeaura.json|JSON (*.json)|*.json", Title = "Открыть обучающий пример" };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        LoadProjectFile(dialog.FileName);
    }

    private void LoadProjectFile(string path)
    {
        try
        {
            var project = HomeAuraProject.FromJson(File.ReadAllText(path, Encoding.UTF8)); _canvas.NewProject(project); _currentPath = path;
            SyncProjectControls();
            _metadataSync = true; _label.SelectedIndex = project.Training.Label == "ACCEPTED" ? 1 : project.Training.Label == "REJECTED" ? 2 : 0; _notes.Text = project.Training.Notes; _metadataSync = false; _canvas.MarkClean(); UpdateTitle(); _status.Text = "Проект открыт";
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Проект не открыт", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }

    private void SaveProject(bool saveAs)
    {
        _canvas.FinishCurrent();
        if (saveAs || string.IsNullOrWhiteSpace(_currentPath))
        {
            using var dialog = new SaveFileDialog { Filter = "HomeAura project (*.homeaura.json)|*.homeaura.json", FileName = "manual-example.homeaura.json", Title = "Сохранить обучающий пример" };
            if (dialog.ShowDialog(this) != DialogResult.OK) return; _currentPath = dialog.FileName;
        }
        try
        {
            _canvas.Project.ValidateContract(); File.WriteAllText(_currentPath!, _canvas.Project.ToJson() + Environment.NewLine, new UTF8Encoding(false)); _canvas.MarkClean(); UpdateTitle(); _status.Text = "Проект сохранён";
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "Проект не сохранён", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }

    private void ExportPng()
    {
        _canvas.FinishCurrent();
        using var dialog = new SaveFileDialog { Filter = "PNG image (*.png)|*.png", FileName = "homeaura-manual-example.png", Title = "Экспортировать вид редактора" };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        try
        {
            using var image = new Bitmap(Math.Max(1, _canvas.ClientSize.Width), Math.Max(1, _canvas.ClientSize.Height));
            _canvas.DrawToBitmap(image, new Rectangle(Point.Empty, image.Size));
            image.Save(dialog.FileName, System.Drawing.Imaging.ImageFormat.Png);
            _status.Text = "PNG экспортирован";
        }
        catch (Exception ex) { MessageBox.Show(this, ex.Message, "PNG не экспортирован", MessageBoxButtons.OK, MessageBoxIcon.Error); }
    }

    protected override void OnFormClosing(FormClosingEventArgs e)
    {
        if (!ConfirmDiscardOrSave()) e.Cancel = true;
        base.OnFormClosing(e);
    }

    private bool ConfirmDiscardOrSave()
    {
        if (!_canvas.IsDirty) return true;
        var result = MessageBox.Show(this, "Сохранить изменения текущего обучающего примера?", "HomeAura", MessageBoxButtons.YesNoCancel, MessageBoxIcon.Question);
        if (result == DialogResult.Cancel) return false;
        if (result == DialogResult.No) return true;
        SaveProject(false);
        return !_canvas.IsDirty;
    }

    private void UpdateTitle()
    {
        var name = string.IsNullOrWhiteSpace(_currentPath) ? "новый проект" : Path.GetFileName(_currentPath);
        Text = $"HomeAura Manual Routing Editor — {name}{(_canvas.IsDirty ? " *" : "")}";
    }

    private void SyncProjectControls()
    {
        _metadataSync = true;
        _gridSpacing.SelectedIndex = _canvas.Project.GridSpacingMm switch { 50 => 0, 200 => 2, _ => 1 };
        var selectedFloorId = _canvas.ActiveFloorId;
        _activeFloor.Items.Clear();
        _activeFloorIds.Clear();
        _activeFloor.Items.Add("Все этажи");
        _activeFloorIds.Add(null);
        foreach (var level in _canvas.Project.Levels)
        {
            _activeFloor.Items.Add($"{level.Id} · {level.Name}");
            _activeFloorIds.Add(level.Id);
        }
        var selectedFloorIndex = selectedFloorId is null ? 0 : _activeFloorIds.IndexOf(selectedFloorId);
        _activeFloor.SelectedIndex = selectedFloorIndex < 0 ? 0 : selectedFloorIndex;
        _metadataSync = false;
    }
}

public sealed class NewProjectDialog : Form
{
    private readonly NumericUpDown _width = new() { Minimum = 2000, Maximum = 100000, Increment = 100, Value = 12000, Width = 140 };
    private readonly NumericUpDown _height = new() { Minimum = 2000, Maximum = 100000, Increment = 100, Value = 8000, Width = 140 };
    public int WidthMm => (int)_width.Value; public int HeightMm => (int)_height.Value;
    public NewProjectDialog()
    {
        Text = "Новый чертёж"; FormBorderStyle = FormBorderStyle.FixedDialog; StartPosition = FormStartPosition.CenterParent; ClientSize = new Size(360, 190); MaximizeBox = MinimizeBox = false;
        var grid = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(20), ColumnCount = 2, RowCount = 3 };
        grid.Controls.Add(new Label { Text = "Ширина, мм", AutoSize = true }, 0, 0); grid.Controls.Add(_width, 1, 0); grid.Controls.Add(new Label { Text = "Высота, мм", AutoSize = true }, 0, 1); grid.Controls.Add(_height, 1, 1);
        var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft }; var ok = new Button { Text = "Создать", DialogResult = DialogResult.OK }; var cancel = new Button { Text = "Отмена", DialogResult = DialogResult.Cancel }; buttons.Controls.Add(ok); buttons.Controls.Add(cancel); grid.Controls.Add(buttons, 0, 2); grid.SetColumnSpan(buttons, 2); Controls.Add(grid); AcceptButton = ok; CancelButton = cancel;
    }
}
