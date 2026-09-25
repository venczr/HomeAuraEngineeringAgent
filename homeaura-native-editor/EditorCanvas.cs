using System.Drawing.Drawing2D;
using System.ComponentModel;

namespace HomeAura.NativeEditor;

public enum EditorTool { Select, Wall, Window, Collector, Circuit }

public sealed class EditorCanvas : Control
{
    private HomeAuraProject _project = HomeAuraProject.CreateBlank();
    private EditorTool _tool = EditorTool.Select;
    private PointMm? _pendingWallStart;
    private PointMm? _pendingWindowStart;
    private string? _pendingWindowWallId;
    private ManualCircuit? _activeCircuit;
    private readonly Stack<HomeAuraProject> _undo = new();
    private readonly Stack<HomeAuraProject> _redo = new();
    private float _zoom = 0.075f;
    private PointF _pan = new(60, 60);
    private Point _lastMouse;
    private bool _panning;
    private PointMm? _hoverPoint;
    private string? _selectedKind;
    private string? _selectedId;
    private string? _activeFloorId;
    private IReadOnlyList<CircuitAnalysis>? _analysisCache;

    public event EventHandler? ProjectChanged;
    public event EventHandler<string>? StatusChanged;
    public event EventHandler? DirtyChanged;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool IsDirty { get; private set; }

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public HomeAuraProject Project
    {
        get => _project;
        set { _project = value; _activeFloorId = null; _analysisCache = null; ResetInteraction(); Invalidate(); ProjectChanged?.Invoke(this, EventArgs.Empty); }
    }

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public string? ActiveFloorId
    {
        get => _activeFloorId;
        set
        {
            if (value is not null && _project.Levels.All(item => item.Id != value))
                throw new ArgumentOutOfRangeException(nameof(value), $"Этаж {value} отсутствует в проекте.");
            _activeFloorId = value;
            ResetInteraction();
            Invalidate();
        }
    }

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public EditorTool Tool
    {
        get => _tool;
        set { _tool = value; _pendingWallStart = null; _pendingWindowStart = null; _pendingWindowWallId = null; if (value != EditorTool.Circuit) FinishCircuit(); Status($"Инструмент: {value}"); Invalidate(); }
    }

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public string NewWallType { get; set; } = "INTERIOR";

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public int NewWallThicknessMm { get; set; } = 200;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool OrthogonalMode { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowRoomLabels { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowServiceLabels { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowCollectorLabels { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowGrid { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowHeatingCircuits { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowServiceCircuits { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowEngineeringDiagnostics { get; set; }

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool Show3DRouteMarkers { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public bool ShowRoutingRoleStyles { get; set; } = true;

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public string NewCircuitRoutingLayer { get; set; } = "HEATING_PLANE";

    [Browsable(false), DesignerSerializationVisibility(DesignerSerializationVisibility.Hidden)]
    public string NewCircuitSystemRole { get; set; } = "FLOOR_HEATING_LOOP";

    public EditorCanvas()
    {
        DoubleBuffered = true;
        BackColor = Color.FromArgb(12, 22, 29);
        Dock = DockStyle.Fill;
        TabStop = true;
        SetStyle(ControlStyles.Selectable, true);
    }

    public void NewProject(HomeAuraProject project)
    {
        _undo.Clear(); _redo.Clear(); Project = project; MarkClean(); FitToProject();
    }

    public void MarkClean() { IsDirty = false; DirtyChanged?.Invoke(this, EventArgs.Empty); }
    public void MarkDirty() { if (IsDirty) return; IsDirty = true; DirtyChanged?.Invoke(this, EventArgs.Empty); }

    public bool TrySetGridSpacing(int spacingMm)
    {
        if (spacingMm is not (50 or 100 or 200)) return false;
        var snapPoints = _project.Collectors.Select(item => item.Position).Concat(_project.Circuits.SelectMany(item => item.OrderedPoints));
        if (snapPoints.Any(point => point.X % spacingMm != 0 || point.Y % spacingMm != 0))
        {
            Status($"Сетка {spacingMm} мм не включена: существующие трубы или коллекторы лежат вне неё");
            return false;
        }
        if (_project.GridSpacingMm == spacingMm) return true;
        Snapshot();
        _project.GridSpacingMm = spacingMm;
        Notify($"Сетка изменена: {spacingMm} мм");
        return true;
    }

    public void Undo()
    {
        if (_undo.Count == 0) return;
        _redo.Push(_project.DeepClone()); _project = _undo.Pop(); ResetInteraction(); MarkDirty(); Notify("Отменено");
    }

    public void Redo()
    {
        if (_redo.Count == 0) return;
        _undo.Push(_project.DeepClone()); _project = _redo.Pop(); ResetInteraction(); MarkDirty(); Notify("Повторено");
    }

    public void FinishCircuit()
    {
        if (_activeCircuit is null) return;
        if (_activeCircuit.CollectorId is null && _activeCircuit.OrderedPoints.Count > 0) AssignCollector(_activeCircuit, _activeCircuit.OrderedPoints[0]);
        _activeCircuit.Completed = _activeCircuit.OrderedPoints.Count >= 2;
        _activeCircuit = null;
        Notify("Контур завершён");
    }

    public void FinishCurrent()
    {
        var hadWall = _pendingWallStart is not null || _pendingWindowStart is not null;
        _pendingWallStart = null;
        _pendingWindowStart = null;
        _pendingWindowWallId = null;
        FinishCircuit();
        if (hadWall) { Invalidate(); Status("Линия стен завершена"); }
    }

    public void DeleteSelection()
    {
        if (_selectedKind is null || _selectedId is null) return;
        Snapshot();
        if (_selectedKind == "wall")
        {
            _project.Windows.RemoveAll(item => item.WallId == _selectedId);
            _project.DoorOpenings?.RemoveAll(item => item.WallId == _selectedId);
            foreach (var collector in _project.Collectors.Where(item => item.MountingWallId == _selectedId))
                collector.MountingWallId = null;
        }
        var removed = _selectedKind switch
        {
            "wall" => _project.Walls.RemoveAll(item => item.Id == _selectedId) > 0,
            "window" => _project.Windows.RemoveAll(item => item.Id == _selectedId) > 0,
            "door" => (_project.DoorOpenings?.RemoveAll(item => item.Id == _selectedId) ?? 0) > 0,
            "collector" => _project.Collectors.RemoveAll(item => item.Id == _selectedId) > 0,
            "circuit" => _project.Circuits.RemoveAll(item => item.Id == _selectedId) > 0,
            _ => false
        };
        if (!removed) { _undo.Pop(); return; }
        _selectedKind = null; _selectedId = null; Notify("Объект удалён");
    }

    public void RotateSelectedCollector()
    {
        if (_selectedKind != "collector" || _selectedId is null)
        {
            Status("Сначала выберите коллектор инструментом «Выбор»");
            return;
        }
        var collector = _project.Collectors.SingleOrDefault(item => item.Id == _selectedId);
        if (collector is null) return;
        Snapshot();
        collector.RotationDegrees = (collector.RotationDegrees + 90) % 360;
        Notify($"Коллектор повёрнут: {collector.RotationDegrees}°");
    }

    public void FitToProject()
    {
        FitToBounds(0, 0, _project.CanvasWidthMm, _project.CanvasHeightMm, 60);
    }

    public bool TryFitToRoom(string roomId, int paddingMm = 400)
    {
        var room = _project.Rooms.SingleOrDefault(item => item.Id == roomId);
        if (room is null || room.Outline.Count < 3) return false;
        ActiveFloorId = room.FloorId;
        FitToBounds(
            room.Outline.Min(point => point.X),
            room.Outline.Min(point => point.Y),
            room.Outline.Max(point => point.X),
            room.Outline.Max(point => point.Y),
            paddingMm);
        return true;
    }

    public void FitToBounds(int minX, int minY, int maxX, int maxY, int paddingMm = 400)
    {
        if (ClientSize.Width <= 0 || ClientSize.Height <= 0 || maxX <= minX || maxY <= minY) return;
        var paddedMinX = Math.Max(0, minX - paddingMm);
        var paddedMinY = Math.Max(0, minY - paddingMm);
        var paddedMaxX = Math.Min(_project.CanvasWidthMm, maxX + paddingMm);
        var paddedMaxY = Math.Min(_project.CanvasHeightMm, maxY + paddingMm);
        var width = Math.Max(1, paddedMaxX - paddedMinX);
        var height = Math.Max(1, paddedMaxY - paddedMinY);
        _zoom = Math.Min((ClientSize.Width - 80f) / width, (ClientSize.Height - 80f) / height);
        _zoom = Math.Clamp(_zoom, 0.01f, 0.5f);
        var centreX = (paddedMinX + paddedMaxX) / 2f;
        var centreY = (paddedMinY + paddedMaxY) / 2f;
        _pan = new PointF(ClientSize.Width / 2f - centreX * _zoom, ClientSize.Height / 2f - centreY * _zoom);
        Invalidate();
    }

    protected override void OnResize(EventArgs e) { base.OnResize(e); if (!DesignMode) FitToProject(); }

    protected override void OnMouseWheel(MouseEventArgs e)
    {
        var before = ScreenToWorld(e.Location);
        _zoom = Math.Clamp(_zoom * (e.Delta > 0 ? 1.15f : 1 / 1.15f), 0.01f, 1f);
        var after = WorldToScreen(before);
        _pan = new PointF(_pan.X + e.X - after.X, _pan.Y + e.Y - after.Y);
        Invalidate();
    }

    protected override void OnMouseDown(MouseEventArgs e)
    {
        Focus();
        if (e.Button == MouseButtons.Middle || e.Button == MouseButtons.Right)
        {
            _panning = true; _lastMouse = e.Location; Cursor = Cursors.SizeAll; return;
        }
        if (e.Button != MouseButtons.Left) return;
        var point = SnapInside(ScreenToWorld(e.Location));
        switch (_tool)
        {
            case EditorTool.Wall: AddWallPoint(point); break;
            case EditorTool.Window: AddWindowPoint(point); break;
            case EditorTool.Collector: AddCollector(point); break;
            case EditorTool.Circuit: AddCircuitPoint(point); break;
            case EditorTool.Select: SelectAt(point); break;
        }
    }

    protected override void OnMouseMove(MouseEventArgs e)
    {
        if (_panning)
        {
            _pan = new PointF(_pan.X + e.X - _lastMouse.X, _pan.Y + e.Y - _lastMouse.Y);
            _lastMouse = e.Location; Invalidate();
        }
        else
        {
            _hoverPoint = SnapInside(ScreenToWorld(e.Location));
            Status($"X {_hoverPoint.X} мм · Y {_hoverPoint.Y} мм");
            Invalidate();
        }
    }

    protected override void OnMouseUp(MouseEventArgs e)
    {
        if (_panning) { _panning = false; Cursor = Cursors.Default; }
    }

    protected override bool IsInputKey(Keys keyData) => keyData is Keys.Enter or Keys.Delete or Keys.R || base.IsInputKey(keyData);

    protected override void OnKeyDown(KeyEventArgs e)
    {
        if (e.Control && e.KeyCode == Keys.Z) { Undo(); e.Handled = true; }
        else if (e.Control && e.KeyCode == Keys.Y) { Redo(); e.Handled = true; }
        else if (e.KeyCode == Keys.Enter) { FinishCurrent(); e.Handled = true; }
        else if (e.KeyCode == Keys.Delete) { DeleteSelection(); e.Handled = true; }
        else if (e.KeyCode == Keys.R) { RotateSelectedCollector(); e.Handled = true; }
        else if (e.KeyCode == Keys.Escape) { _pendingWallStart = null; _pendingWindowStart = null; _pendingWindowWallId = null; FinishCircuit(); Invalidate(); e.Handled = true; }
        base.OnKeyDown(e);
    }

    private void AddWallPoint(PointMm point)
    {
        if (_project.SchemaVersion == "1.1" && _project.Levels.Count > 1 && ActiveFloorId is null)
        {
            Status("Сначала выберите активный этаж: стена schema 1.1 не может быть без floor_id");
            return;
        }
        if (_pendingWallStart is null) { _pendingWallStart = point; Status("Укажите конец стены"); Invalidate(); return; }
        point = ConstrainPoint(_pendingWallStart, point);
        if (_pendingWallStart.X == point.X && _pendingWallStart.Y == point.Y) return;
        Snapshot();
        _project.Walls.Add(new WallSegment
        {
            Start = _pendingWallStart.Clone(), End = point.Clone(), WallType = NewWallType,
            ThicknessMm = NewWallThicknessMm, FloorId = _project.SchemaVersion == "1.1" ? ActiveFloorId : null,
        });
        _pendingWallStart = point.Clone(); Notify("Стена добавлена. Следующая точка продолжит линию; Enter — закончить");
    }

    private void AddWindowPoint(PointMm point)
    {
        if (_project.SchemaVersion == "1.1" && _project.Levels.Count > 1 && ActiveFloorId is null)
        {
            Status("Сначала выберите активный этаж: окно schema 1.1 не может быть без floor_id");
            return;
        }
        if (_pendingWindowStart is null)
        {
            var nearest = _project.Walls
                .Where(item => IsFloorVisible(item.FloorId))
                .Select(item => (Item: item, Distance: PointToSegmentDistance(point, item.Start, item.End)))
                .Where(item => item.Distance <= 400).OrderBy(item => item.Distance).FirstOrDefault();
            if (nearest.Item is null) { Status("Щёлкните по стене: окно всегда привязывается к стене"); return; }
            _pendingWindowWallId = nearest.Item.Id;
            _pendingWindowStart = ProjectPointToSegment(point, nearest.Item.Start, nearest.Item.End);
            Status("Укажите второй край окна вдоль этой же стены"); Invalidate(); return;
        }
        var wall = _project.Walls.SingleOrDefault(item => item.Id == _pendingWindowWallId);
        if (wall is null) { _pendingWindowStart = null; _pendingWindowWallId = null; Status("Стена окна больше не существует"); return; }
        point = ProjectPointToSegment(point, wall.Start, wall.End);
        if (_pendingWindowStart.X == point.X && _pendingWindowStart.Y == point.Y) return;
        Snapshot();
        _project.Windows.Add(new WindowOpening
        {
            Start = _pendingWindowStart.Clone(), End = point.Clone(), WallId = wall.Id,
            FloorId = _project.SchemaVersion == "1.1" ? wall.FloorId ?? ActiveFloorId : null,
        });
        _pendingWindowStart = null; _pendingWindowWallId = null; Notify("Окно добавлено голубым участком стены");
    }

    private void AddCollector(PointMm point)
    {
        if (_project.SchemaVersion == "1.1" && _project.Levels.Count > 1 && ActiveFloorId is null)
        {
            Status("Сначала выберите активный этаж: коллектор schema 1.1 требует этаж установки");
            return;
        }
        var floorId = _project.SchemaVersion == "1.1"
            ? ActiveFloorId ?? _project.Levels.SingleOrDefault()?.Id
            : null;
        Snapshot();
        var collector = new Collector { Position = point.Clone(), FloorId = floorId, ServedFloorId = floorId };
        _project.Collectors.Add(collector);
        _selectedKind = "collector"; _selectedId = collector.Id;
        Notify("Коллектор добавлен и выбран. R — повернуть на 90°");
    }

    private void AddCircuitPoint(PointMm point)
    {
        if (_activeCircuit is null)
        {
            if (_project.SchemaVersion == "1.1" && _project.Levels.Count > 1 && ActiveFloorId is null)
            {
                Status("Сначала выберите активный этаж: трассу schema 1.1 нельзя назначить неоднозначному коллектору");
                return;
            }
            Snapshot();
            var index = _project.Circuits.Count;
            _activeCircuit = new ManualCircuit
            {
                Name = $"Контур {index + 1}", Color = Palette[index % Palette.Length],
                RoutingLayer = NewCircuitRoutingLayer, SystemRole = NewCircuitSystemRole
            };
            AssignCollector(_activeCircuit, point);
            _project.Circuits.Add(_activeCircuit);
        }
        var last = _activeCircuit.OrderedPoints.LastOrDefault();
        if (last is not null) point = ConstrainPoint(last, point);
        if (last is not null && last.X == point.X && last.Y == point.Y) return;
        _activeCircuit.OrderedPoints.Add(point.Clone());
        Notify($"{_activeCircuit.Name}: точек {_activeCircuit.OrderedPoints.Count}. Enter — завершить");
    }

    private void Snapshot() { _undo.Push(_project.DeepClone()); _redo.Clear(); MarkDirty(); }
    private void Notify(string message) { _analysisCache = null; Invalidate(); ProjectChanged?.Invoke(this, EventArgs.Empty); Status(message); }
    private void Status(string message) => StatusChanged?.Invoke(this, message);
    private void ResetInteraction() { _pendingWallStart = null; _pendingWindowStart = null; _pendingWindowWallId = null; _activeCircuit = null; _selectedKind = null; _selectedId = null; }

    private PointMm ConstrainPoint(PointMm origin, PointMm point)
    {
        if (!OrthogonalMode) return point;
        return Math.Abs(point.X - origin.X) >= Math.Abs(point.Y - origin.Y)
            ? new PointMm(point.X, origin.Y)
            : new PointMm(origin.X, point.Y);
    }

    private void AssignCollector(ManualCircuit circuit, PointMm point)
    {
        var candidates = _project.Collectors.AsEnumerable();
        if (ActiveFloorId is not null)
        {
            candidates = circuit.SystemRole is "FLOOR_HEATING_LOOP" or "FLOOR_HEATING_AXIS"
                ? candidates.Where(item => item.ServedFloorId == ActiveFloorId ||
                                           string.IsNullOrWhiteSpace(item.ServedFloorId) && item.FloorId == ActiveFloorId)
                : candidates.Where(item => item.FloorId == ActiveFloorId || item.ServedFloorId == ActiveFloorId);
        }
        var collector = candidates.OrderBy(item => CircuitAnalyzer.Distance(item.Position, point)).FirstOrDefault();
        if (collector is null) return;
        var used = _project.Circuits.Where(item => item.Id != circuit.Id && item.CollectorId == collector.Id)
            .SelectMany(item => new[] { item.SupplyPortIndex, item.ReturnPortIndex }).Where(item => item is not null).Select(item => item!.Value).ToHashSet();
        var free = Enumerable.Range(0, collector.ConnectionCapacity).Where(index => !used.Contains(index)).Take(2).ToArray();
        if (free.Length < 2) return;
        circuit.CollectorId = collector.Id; circuit.SupplyPortIndex = free[0]; circuit.ReturnPortIndex = free[1];
    }

    private void SelectAt(PointMm point)
    {
        _selectedKind = null; _selectedId = null;
        var collector = _project.Collectors
            .Where(item => IsFloorVisible(item.FloorId))
            .Select(item => (Item: item, Distance: CircuitAnalyzer.Distance(item.Position, point)))
            .Where(item => item.Distance <= 350).OrderBy(item => item.Distance).FirstOrDefault();
        if (collector.Item is not null) { _selectedKind = "collector"; _selectedId = collector.Item.Id; Status("Выбран коллектор. Delete — удалить"); Invalidate(); return; }

        var window = _project.Windows
            .Where(item => IsFloorVisible(item.FloorId))
            .Select(item => (Item: item, Distance: PointToSegmentDistance(point, item.Start, item.End)))
            .Where(item => item.Distance <= 180).OrderBy(item => item.Distance).FirstOrDefault();
        if (window.Item is not null) { _selectedKind = "window"; _selectedId = window.Item.Id; Status("Выбрано окно. Delete — удалить"); Invalidate(); return; }

        var door = (_project.DoorOpenings ?? [])
            .Where(item => IsFloorVisible(item.FloorId))
            .Select(item => (Item: item, Distance: PointToSegmentDistance(point, item.Start, item.End)))
            .Where(item => item.Distance <= 180).OrderBy(item => item.Distance).FirstOrDefault();
        if (door.Item is not null) { _selectedKind = "door"; _selectedId = door.Item.Id; Status("Выбрана дверь. Delete — удалить"); Invalidate(); return; }

        var circuit = _project.Circuits
            .Where(IsCircuitVisible)
            .Select(item => (Item: item, Distance: MinimumDistance(item.OrderedPoints, point)))
            .Where(item => item.Distance <= 180).OrderBy(item => item.Distance).FirstOrDefault();
        if (circuit.Item is not null) { _selectedKind = "circuit"; _selectedId = circuit.Item.Id; Status($"Выбран {circuit.Item.Name}. Delete — удалить"); Invalidate(); return; }

        var wall = _project.Walls
            .Where(item => IsFloorVisible(item.FloorId))
            .Select(item => (Item: item, Distance: PointToSegmentDistance(point, item.Start, item.End)))
            .Where(item => item.Distance <= 180).OrderBy(item => item.Distance).FirstOrDefault();
        if (wall.Item is not null) { _selectedKind = "wall"; _selectedId = wall.Item.Id; Status("Выбрана стена. Delete — удалить"); Invalidate(); return; }
        Status($"Координата: {point.X} × {point.Y} мм"); Invalidate();
    }

    private bool IsFloorVisible(string? floorId) =>
        ActiveFloorId is null || string.IsNullOrWhiteSpace(floorId) || floorId == ActiveFloorId;

    private bool IsCircuitOnActiveFloor(ManualCircuit circuit)
    {
        if (ActiveFloorId is null) return true;
        var collector = circuit.CollectorId is null
            ? null
            : _project.Collectors.SingleOrDefault(item => item.Id == circuit.CollectorId);
        if (collector is not null && !string.IsNullOrWhiteSpace(collector.FloorId) &&
            !string.IsNullOrWhiteSpace(collector.ServedFloorId) && collector.FloorId != collector.ServedFloorId)
            return true;
        var roomFloor = circuit.RoomId is null
            ? null
            : _project.Rooms.SingleOrDefault(item => item.Id == circuit.RoomId)?.FloorId;
        var floorId = !string.IsNullOrWhiteSpace(roomFloor)
            ? roomFloor
            : !string.IsNullOrWhiteSpace(collector?.ServedFloorId)
                ? collector.ServedFloorId
                : collector?.FloorId;
        return string.IsNullOrWhiteSpace(floorId) || floorId == ActiveFloorId;
    }

    private static PointMm ProjectPointToSegment(PointMm point, PointMm start, PointMm end)
    {
        var dx = end.X - start.X; var dy = end.Y - start.Y;
        if (dx == 0 && dy == 0) return start.Clone();
        var denominator = (double)dx * dx + (double)dy * dy;
        var t = Math.Clamp(((double)(point.X - start.X) * dx + (double)(point.Y - start.Y) * dy) / denominator, 0d, 1d);
        return new PointMm((int)Math.Round(start.X + t * dx), (int)Math.Round(start.Y + t * dy));
    }

    private static double MinimumDistance(IReadOnlyList<PointMm> points, PointMm point)
    {
        if (points.Count == 0) return double.MaxValue;
        if (points.Count == 1) return CircuitAnalyzer.Distance(points[0], point);
        return Enumerable.Range(1, points.Count - 1).Min(index => PointToSegmentDistance(point, points[index - 1], points[index]));
    }

    private static double PointToSegmentDistance(PointMm point, PointMm start, PointMm end)
    {
        var dx = end.X - start.X; var dy = end.Y - start.Y;
        if (dx == 0 && dy == 0) return CircuitAnalyzer.Distance(point, start);
        var t = Math.Clamp(((point.X - start.X) * dx + (point.Y - start.Y) * dy) / (double)(dx * dx + dy * dy), 0, 1);
        var x = start.X + t * dx; var y = start.Y + t * dy;
        return Math.Sqrt(Math.Pow(point.X - x, 2) + Math.Pow(point.Y - y, 2));
    }

    private PointMm ScreenToWorld(Point point) => new((int)((point.X - _pan.X) / _zoom), (int)((ClientSize.Height - point.Y - _pan.Y) / _zoom));
    private PointF WorldToScreen(PointMm point) => new(_pan.X + point.X * _zoom, ClientSize.Height - _pan.Y - point.Y * _zoom);
    private PointF WorldToScreen(Point3Mm point) => new(
        _pan.X + (float)(point.X * _zoom),
        ClientSize.Height - _pan.Y - (float)(point.Y * _zoom));
    private PointMm SnapInside(PointMm point)
    {
        var snapped = CircuitAnalyzer.Snap(point.X, point.Y, _project.GridSpacingMm);
        snapped.X = Math.Clamp(snapped.X, 0, _project.CanvasWidthMm);
        snapped.Y = Math.Clamp(snapped.Y, 0, _project.CanvasHeightMm);
        return snapped;
    }

    protected override void OnPaint(PaintEventArgs e)
    {
        base.OnPaint(e);
        e.Graphics.SmoothingMode = SmoothingMode.AntiAlias;
        if (ShowGrid) DrawGrid(e.Graphics);
        DrawLevelsAndRooms(e.Graphics);
        DrawWalls(e.Graphics);
        DrawWindows(e.Graphics);
        DrawDoors(e.Graphics);
        DrawInterfloorOpenings(e.Graphics);
        DrawCircuits(e.Graphics);
        if (Show3DRouteMarkers) Draw3DRouteMarkers(e.Graphics);
        if (ShowEngineeringDiagnostics) DrawEngineeringDiagnostics(e.Graphics);
        DrawCollectors(e.Graphics);
        DrawPending(e.Graphics);
    }

    private void DrawLevelsAndRooms(Graphics g)
    {
        foreach (var level in _project.Levels)
        {
            if (!IsFloorVisible(level.Id)) continue;
            if (level.Outline.Count < 3) continue;
            using var fill = new SolidBrush(Color.FromArgb(95, 15, 39, 49));
            using var pen = new Pen(Color.FromArgb(148, 163, 184), 2.5f);
            var points = level.Outline.Select(WorldToScreen).ToArray();
            g.FillPolygon(fill, points); g.DrawPolygon(pen, points);
            var lp = WorldToScreen(level.LabelPosition);
            using var font = new Font("Segoe UI", 12, FontStyle.Bold);
            using var brush = new SolidBrush(Color.FromArgb(226, 232, 240));
            g.DrawString(level.Name, font, brush, lp);
        }
        foreach (var room in _project.Rooms)
        {
            if (!IsFloorVisible(room.FloorId)) continue;
            if (room.Outline.Count < 3) continue;
            var baseColor = ColorTranslator.FromHtml(room.FillColor);
            using var fill = new SolidBrush(Color.FromArgb(room.HeatingAllowed ? 58 : 35, baseColor));
            using var pen = new Pen(Color.FromArgb(95, 170, 185, 194), 1.4f);
            var points = room.Outline.Select(WorldToScreen).ToArray();
            g.FillPolygon(fill, points); g.DrawPolygon(pen, points);
            if (ShowRoomLabels)
            {
                var lp = WorldToScreen(room.LabelPosition);
                using var font = new Font("Segoe UI", 8.5f, FontStyle.Regular);
                using var brush = new SolidBrush(Color.FromArgb(184, 216, 225));
                var text = room.AreaM2 is null ? room.Name : $"{room.Name}  {room.AreaM2:0.#} м²";
                var size = g.MeasureString(text, font);
                using var labelBackground = new SolidBrush(Color.FromArgb(178, 7, 22, 29));
                g.FillRectangle(labelBackground, lp.X - 3, lp.Y - 2, size.Width + 6, size.Height + 4);
                g.DrawString(text, font, brush, lp);
            }
        }
        foreach (var zone in _project.Exclusions)
        {
            if (!IsFloorVisible(zone.FloorId)) continue;
            if (zone.Outline.Count < 3) continue;
            var baseColor = ColorTranslator.FromHtml(zone.FillColor);
            using var fill = new SolidBrush(Color.FromArgb(95, baseColor));
            using var pen = new Pen(Color.FromArgb(248, 113, 113), 2) { DashStyle = DashStyle.Dash };
            var points = zone.Outline.Select(WorldToScreen).ToArray();
            g.FillPolygon(fill, points); g.DrawPolygon(pen, points);
        }
        foreach (var zone in _project.ServiceZones)
        {
            if (!IsFloorVisible(zone.FloorId)) continue;
            if (zone.Outline.Count < 3) continue;
            var baseColor = ColorTranslator.FromHtml(zone.FillColor);
            using var fill = new SolidBrush(Color.FromArgb(42, baseColor));
            var outlineColor = zone.PipeGeometryMaterialized ? Color.FromArgb(45, 212, 191) : Color.FromArgb(251, 191, 36);
            using var pen = new Pen(outlineColor, 2) { DashStyle = zone.PipeGeometryMaterialized ? DashStyle.Solid : DashStyle.DashDot };
            var points = zone.Outline.Select(WorldToScreen).ToArray();
            g.FillPolygon(fill, points); g.DrawPolygon(pen, points);
            if (ShowServiceLabels)
            {
                var left = zone.Outline.Min(item => item.X); var top = zone.Outline.Min(item => item.Y);
                using var font = new Font("Segoe UI", 8.5f, FontStyle.Bold);
                using var brush = new SolidBrush(zone.PipeGeometryMaterialized ? Color.FromArgb(153, 246, 228) : Color.FromArgb(253, 230, 138));
                var labelPoint = WorldToScreen(new PointMm(left + 150, top + 250));
                var reservation = zone.RequiredPipeCount is null
                    ? "РЕЗЕРВ"
                    : $"РЕЗЕРВ {zone.RequiredPipeCount}×";
                if (zone.RequiredPlanWidthMm is not null)
                    reservation += $" · {zone.RequiredPlanWidthMm / 1000d:0.0}м";
                var label = zone.PipeGeometryMaterialized ? zone.Name : reservation;
                var size = g.MeasureString(label, font);
                using var labelBackground = new SolidBrush(Color.FromArgb(190, 7, 22, 29));
                g.FillRectangle(labelBackground, labelPoint.X - 3, labelPoint.Y - 2, size.Width + 6, size.Height + 4);
                g.DrawString(label, font, brush, labelPoint);
            }
        }
    }

    private void DrawGrid(Graphics g)
    {
        var topLeft = WorldToScreen(new PointMm(0, _project.CanvasHeightMm));
        var bottomRight = WorldToScreen(new PointMm(_project.CanvasWidthMm, 0));
        using var background = new SolidBrush(Color.FromArgb(10, 29, 37));
        g.FillRectangle(background, topLeft.X, topLeft.Y, bottomRight.X - topLeft.X, bottomRight.Y - topLeft.Y);
        var minor = Color.FromArgb(35, 62, 72); var major = Color.FromArgb(55, 86, 98);
        for (var x = 0; x <= _project.CanvasWidthMm; x += _project.GridSpacingMm)
        {
            var p1 = WorldToScreen(new PointMm(x, 0)); var p2 = WorldToScreen(new PointMm(x, _project.CanvasHeightMm));
            using var pen = new Pen(x % 1000 == 0 ? major : minor, x % 1000 == 0 ? 1.2f : .45f); g.DrawLine(pen, p1, p2);
        }
        for (var y = 0; y <= _project.CanvasHeightMm; y += _project.GridSpacingMm)
        {
            var p1 = WorldToScreen(new PointMm(0, y)); var p2 = WorldToScreen(new PointMm(_project.CanvasWidthMm, y));
            using var pen = new Pen(y % 1000 == 0 ? major : minor, y % 1000 == 0 ? 1.2f : .45f); g.DrawLine(pen, p1, p2);
        }
        using var border = new Pen(Color.FromArgb(135, 165, 175), 2); g.DrawRectangle(border, topLeft.X, topLeft.Y, bottomRight.X - topLeft.X, bottomRight.Y - topLeft.Y);
    }

    private void DrawWalls(Graphics g)
    {
        foreach (var wall in _project.Walls)
        {
            if (!IsFloorVisible(wall.FloorId)) continue;
            var selected = _selectedKind == "wall" && _selectedId == wall.Id;
            var unscoped = _project.SchemaVersion == "1.1" && ActiveFloorId is not null && string.IsNullOrWhiteSpace(wall.FloorId);
            var width = Math.Max(3f, wall.ThicknessMm * _zoom);
            var color = selected ? Color.FromArgb(253, 224, 71) : unscoped ? Color.FromArgb(251, 191, 36) :
                wall.WallType == "EXTERIOR" ? Color.FromArgb(196, 181, 155) : Color.FromArgb(218, 231, 236);
            using var pen = new Pen(color, selected ? width + 4 : width) { StartCap = LineCap.Square, EndCap = LineCap.Square };
            g.DrawLine(pen, WorldToScreen(wall.Start), WorldToScreen(wall.End));
        }
    }

    private void DrawWindows(Graphics g)
    {
        foreach (var window in _project.Windows)
        {
            if (!IsFloorVisible(window.FloorId)) continue;
            var wallThickness = window.WallId is null ? 200 : _project.Walls.FirstOrDefault(item => item.Id == window.WallId)?.ThicknessMm ?? 200;
            var width = Math.Max(4f, wallThickness * _zoom * .72f);
            var selected = _selectedKind == "window" && _selectedId == window.Id;
            var unscoped = _project.SchemaVersion == "1.1" && ActiveFloorId is not null && string.IsNullOrWhiteSpace(window.FloorId);
            using var underlay = new Pen(Color.FromArgb(10, 29, 37), width + 3) { StartCap = LineCap.Square, EndCap = LineCap.Square };
            using var glass = new Pen(selected ? Color.FromArgb(253, 224, 71) : unscoped ? Color.FromArgb(251, 191, 36) : Color.FromArgb(125, 211, 252), width) { StartCap = LineCap.Square, EndCap = LineCap.Square };
            g.DrawLine(underlay, WorldToScreen(window.Start), WorldToScreen(window.End));
            g.DrawLine(glass, WorldToScreen(window.Start), WorldToScreen(window.End));
        }
    }

    private void DrawDoors(Graphics g)
    {
        foreach (var door in _project.DoorOpenings ?? [])
        {
            if (!IsFloorVisible(door.FloorId)) continue;
            var wallThickness = _project.Walls.FirstOrDefault(item => item.Id == door.WallId)?.ThicknessMm ?? 200;
            var width = Math.Max(4f, wallThickness * _zoom * .72f);
            var selected = _selectedKind == "door" && _selectedId == door.Id;
            var verified = door.PhysicalVerification?.Status == "INDEPENDENTLY_VERIFIED";
            using var underlay = new Pen(Color.FromArgb(10, 29, 37), width + 3) { StartCap = LineCap.Square, EndCap = LineCap.Square };
            using var leaf = new Pen(selected ? Color.FromArgb(253, 224, 71) : verified ? Color.FromArgb(74, 222, 128) : Color.FromArgb(251, 191, 36), width)
            { StartCap = LineCap.Square, EndCap = LineCap.Square, DashStyle = verified ? DashStyle.Solid : DashStyle.Dash };
            g.DrawLine(underlay, WorldToScreen(door.Start), WorldToScreen(door.End));
            g.DrawLine(leaf, WorldToScreen(door.Start), WorldToScreen(door.End));
        }
    }

    private void DrawInterfloorOpenings(Graphics g)
    {
        foreach (var opening in _project.InterfloorOpenings ?? [])
        {
            var faces = new[] { opening.FromFloorFace, opening.ToFloorFace }
                .Where(face => face is not null && IsFloorVisible(face.FloorId) && face.VerifiedPlanOutlineMm.Count >= 3)
                .ToArray();
            foreach (var face in faces)
            {
                var points = face.VerifiedPlanOutlineMm.Select(WorldToScreen).ToArray();
                using var fill = new SolidBrush(Color.FromArgb(42, 168, 85, 247));
                using var pen = new Pen(Color.FromArgb(216, 180, 254), 2.5f) { DashStyle = DashStyle.Dash };
                g.FillPolygon(fill, points);
                g.DrawPolygon(pen, points);
                if (!ShowRoomLabels) continue;
                var centre = new PointF(points.Average(item => item.X), points.Average(item => item.Y));
                using var font = new Font("Segoe UI", 7.5f, FontStyle.Bold);
                using var brush = new SolidBrush(Color.FromArgb(233, 213, 255));
                g.DrawString($"{opening.Id} · {opening.FromFloorId}→{opening.ToFloorId}", font, brush, centre);
            }
        }
    }

    private void DrawCollectors(Graphics g)
    {
        foreach (var collector in _project.Collectors)
        {
            if (!collector.VisibleOnPlan) continue;
            if (!IsFloorVisible(collector.FloorId)) continue;
            if (collector.HasPhysicalReferenceGeometry)
            {
                DrawPhysicalCollector(g, collector);
                continue;
            }

            DrawLegacyCollector(g, collector);
        }
    }

    private void DrawLegacyCollector(Graphics g, Collector collector)
    {
            var p = WorldToScreen(collector.Position);
            var selected = _selectedKind == "collector" && _selectedId == collector.Id;
            using var pen = new Pen(selected ? Color.FromArgb(253, 224, 71) : Color.FromArgb(203, 213, 225), selected ? 4 : 2);
            var stations = Math.Max(1, (int)Math.Ceiling(collector.Ports / 2d));
            var bodyWidth = Math.Max(28f, collector.ReferenceWidthMm * _zoom);
            var bodyDepth = Math.Max(20f, collector.ReferenceDepthMm * _zoom);
            var stationPitch = bodyWidth / Math.Max(stations, 1);
            var state = g.Save();
            g.TranslateTransform(p.X, p.Y); g.RotateTransform(collector.RotationDegrees);
            using var supply = new Pen(Color.FromArgb(248, 113, 113), 5) { StartCap = LineCap.Round, EndCap = LineCap.Round };
            using var returnRail = new Pen(Color.FromArgb(96, 165, 250), 5) { StartCap = LineCap.Round, EndCap = LineCap.Round };
            var railOffset = bodyDepth * .23f;
            g.DrawLine(supply, -bodyWidth / 2f, -railOffset, bodyWidth / 2f, -railOffset);
            g.DrawLine(returnRail, -bodyWidth / 2f, railOffset, bodyWidth / 2f, railOffset);
            g.DrawRectangle(pen, -bodyWidth / 2f - 4, -bodyDepth / 2f, bodyWidth + 8, bodyDepth);
            for (var i = 0; i < stations; i++)
            {
                var x = -bodyWidth / 2f + stationPitch / 2f + i * stationPitch;
                using var meter = new SolidBrush(Color.FromArgb(219, 234, 254));
                g.FillRectangle(meter, x - .7f, -bodyDepth / 2f - 4, 1.4f, Math.Max(4, bodyDepth / 2f - railOffset));
                g.FillEllipse(Brushes.White, x - 1f, railOffset - 1, 2f, 2f);
            }
            g.DrawLine(pen, -bodyWidth / 2f - 8, -railOffset, -bodyWidth / 2f - 4, -railOffset);
            g.DrawLine(pen, -bodyWidth / 2f - 8, railOffset, -bodyWidth / 2f - 4, railOffset);
            g.Restore(state);
            var arrowStart = collector.PipeOutletDirection == "UP" ? p.Y - 15 : p.Y + 15;
            var arrowEnd = collector.PipeOutletDirection == "UP" ? p.Y - 27 : p.Y + 27;
            g.DrawLine(pen, p.X, arrowStart, p.X, arrowEnd);
            g.DrawLine(pen, p.X, arrowEnd, p.X - 4, arrowEnd + (collector.PipeOutletDirection == "UP" ? 5 : -5));
            g.DrawLine(pen, p.X, arrowEnd, p.X + 4, arrowEnd + (collector.PipeOutletDirection == "UP" ? 5 : -5));
            if (ShowCollectorLabels)
            {
                using var labelFont = new Font("Segoe UI", 7.5f, FontStyle.Bold);
                using var labelBrush = new SolidBrush(Color.FromArgb(153, 246, 228));
                var direction = collector.PipeOutletDirection == "UP" ? "↑" : "↓";
                var labelY = collector.PipeOutletDirection == "UP" ? p.Y + 18 : p.Y - 35;
                var status = collector.EquipmentStatus == "DRAFT_UNSELECTED" ? " · габарит-референс" : "";
                var label = $"{collector.Id} · {stations} петель {direction} · {collector.ReferenceWidthMm}×{collector.ReferenceDepthMm} мм{status}";
                var labelSize = g.MeasureString(label, labelFont);
                using var labelBackground = new SolidBrush(Color.FromArgb(205, 7, 22, 29));
                g.FillRectangle(labelBackground, p.X + 10, labelY - 1, labelSize.Width + 4, labelSize.Height + 2);
                g.DrawString(label, labelFont, labelBrush, p.X + 12, labelY);
            }
    }

    private void DrawPhysicalCollector(Graphics g, Collector collector)
    {
        var centre = WorldToScreen(collector.Position);
        var selected = _selectedKind == "collector" && _selectedId == collector.Id;
        var bodyLength = collector.ReferenceLengthMm!.Value * _zoom;
        var bodyDepth = collector.ReferenceDepthMm * _zoom;
        var headerPitch = collector.HeaderPitchMm!.Value * _zoom;
        var worldAngle = collector.MountingWallAngleDegrees(_project) + collector.RotationDegrees;
        var screenAngle = (float)-worldAngle;
        var connectionPoints = collector.ResolveConnectionPoints();

        using var outline = new Pen(selected ? Color.FromArgb(253, 224, 71) : Color.FromArgb(203, 213, 225), selected ? 4 : 1.5f);
        using var supply = new Pen(Color.FromArgb(248, 113, 113), Math.Max(2f, 22f * _zoom)) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        using var returnRail = new Pen(Color.FromArgb(96, 165, 250), Math.Max(2f, 22f * _zoom)) { StartCap = LineCap.Round, EndCap = LineCap.Round };
        using var bracket = new Pen(Color.FromArgb(148, 163, 184), Math.Max(1f, 6f * _zoom));
        using var meterBrush = new SolidBrush(Color.FromArgb(219, 234, 254));
        using var supplyBrush = new SolidBrush(Color.FromArgb(254, 202, 202));
        using var returnBrush = new SolidBrush(Color.FromArgb(191, 219, 254));

        var state = g.Save();
        g.TranslateTransform(centre.X, centre.Y);
        g.RotateTransform(screenAngle);
        var supplyY = headerPitch / 2f;
        var returnY = -headerPitch / 2f;
        g.DrawRectangle(outline, -bodyLength / 2f, -bodyDepth / 2f, bodyLength, bodyDepth);
        g.DrawLine(supply, -bodyLength / 2f, supplyY, bodyLength / 2f, supplyY);
        g.DrawLine(returnRail, -bodyLength / 2f, returnY, bodyLength / 2f, returnY);

        var bracketInset = Math.Min(bodyLength * .16f, 100f * _zoom);
        g.DrawLine(bracket, -bodyLength / 2f + bracketInset, -bodyDepth / 2f, -bodyLength / 2f + bracketInset, bodyDepth / 2f);
        g.DrawLine(bracket, bodyLength / 2f - bracketInset, -bodyDepth / 2f, bodyLength / 2f - bracketInset, bodyDepth / 2f);

        foreach (var connection in connectionPoints)
        {
            var x = (float)connection.LocalPositionMm.X * _zoom;
            var y = (float)-connection.LocalPositionMm.Y * _zoom;
            var radius = Math.Max(1.7f, 7f * _zoom);
            var brush = connection.Header == "SUPPLY" ? supplyBrush : returnBrush;
            g.FillEllipse(brush, x - radius, y - radius, radius * 2, radius * 2);
            g.DrawEllipse(outline, x - radius, y - radius, radius * 2, radius * 2);
            if (connection.Header == "SUPPLY")
            {
                var meterHeight = Math.Max(3f, (bodyDepth / 2f - supplyY) * .75f);
                g.FillRectangle(meterBrush, x - Math.Max(1f, 5f * _zoom), supplyY + radius,
                    Math.Max(2f, 10f * _zoom), meterHeight);
            }
        }

        var firstSupply = connectionPoints.First(item => item.Header == "SUPPLY");
        var markerX = (float)firstSupply.LocalPositionMm.X * _zoom;
        var markerY = supplyY;
        var markerSize = Math.Max(3f, 18f * _zoom);
        using var markerBrush = new SolidBrush(Color.FromArgb(253, 224, 71));
        g.FillPolygon(markerBrush,
        [
            new PointF(markerX - markerSize, markerY),
            new PointF(markerX - markerSize * 1.8f, markerY - markerSize * .65f),
            new PointF(markerX - markerSize * 1.8f, markerY + markerSize * .65f),
        ]);
        g.Restore(state);

        DrawCollectorOutletArrow(g, collector, centre, outline);
        if (!ShowCollectorLabels) return;

        using var labelFont = new Font("Segoe UI", 7.5f, FontStyle.Bold);
        using var labelBrush = new SolidBrush(Color.FromArgb(153, 246, 228));
        using var labelBackground = new SolidBrush(Color.FromArgb(215, 7, 22, 29));
        var direction = collector.PipeOutletDirection switch { "UP" => "↑", "LEFT" => "←", "RIGHT" => "→", _ => "↓" };
        var labelY = collector.PipeOutletDirection == "UP" ? centre.Y + 18 : centre.Y - 35;
        var model = string.IsNullOrWhiteSpace(collector.Model) ? "коллектор" : collector.Model;
        if (model.Length > 30) model = $"{model[..29]}…";
        var firstLine = $"{collector.Id} · {model} · {collector.RotationDegrees}° {direction}";
        var part = string.IsNullOrWhiteSpace(collector.PartNumber) ? "" : $" · арт. {collector.PartNumber}";
        var secondLine = $"{collector.LoopCount} петель / {collector.ConnectionCapacity} точек · {collector.ReferenceLengthMm}×{collector.ReferenceDepthMm} мм{part}";
        var firstSize = g.MeasureString(firstLine, labelFont);
        var secondSize = g.MeasureString(secondLine, labelFont);
        var labelWidth = Math.Max(firstSize.Width, secondSize.Width);
        var labelHeight = firstSize.Height + secondSize.Height;
        g.FillRectangle(labelBackground, centre.X + 10, labelY - 1, labelWidth + 4, labelHeight + 2);
        g.DrawString(firstLine, labelFont, labelBrush, centre.X + 12, labelY);
        g.DrawString(secondLine, labelFont, labelBrush, centre.X + 12, labelY + firstSize.Height);
    }

    private static void DrawCollectorOutletArrow(Graphics g, Collector collector, PointF centre, Pen pen)
    {
        var direction = collector.PipeOutletDirection switch
        {
            "UP" => new PointF(0, -1),
            "LEFT" => new PointF(-1, 0),
            "RIGHT" => new PointF(1, 0),
            _ => new PointF(0, 1),
        };
        var start = new PointF(centre.X + direction.X * 15, centre.Y + direction.Y * 15);
        var end = new PointF(centre.X + direction.X * 27, centre.Y + direction.Y * 27);
        g.DrawLine(pen, start, end);
        var normal = new PointF(-direction.Y, direction.X);
        g.DrawLine(pen, end, new PointF(end.X - direction.X * 5 + normal.X * 4, end.Y - direction.Y * 5 + normal.Y * 4));
        g.DrawLine(pen, end, new PointF(end.X - direction.X * 5 - normal.X * 4, end.Y - direction.Y * 5 - normal.Y * 4));
    }

    private void DrawCircuits(Graphics g)
    {
        var ordered = _project.Circuits
            .Where(IsCircuitVisible)
            .OrderBy(item => item.RoutingLayer == "HEATING_PLANE" ? 1 : 0);
        foreach (var circuit in ordered)
        {
            if (circuit.OrderedPoints.Count < 2) continue;
            var serviceLayer = circuit.RoutingLayer != "HEATING_PLANE";
            var selected = _selectedKind == "circuit" && _selectedId == circuit.Id;
            if (!ShowRoutingRoleStyles)
            {
                var roundedAxis = CircuitAnalyzer.SampleRoundedPlanAxis(
                    circuit,
                    _project.RoutingRules.MinimumBendRadiusMm);
                var cleanPoints = roundedAxis.SampledPoints.Select(WorldToScreen).ToArray();
                using var cleanPen = new Pen(
                    selected ? Color.FromArgb(253, 224, 71) : ColorTranslator.FromHtml(circuit.Color),
                    selected ? 5 : 2.6f)
                {
                    LineJoin = LineJoin.Round,
                    StartCap = LineCap.Round,
                    EndCap = LineCap.Round,
                };
                if (circuit.RoutingLayer == "VERTICAL_RISER_PROJECTION") cleanPen.DashStyle = DashStyle.Dot;
                g.DrawLines(cleanPen, cleanPoints);
                continue;
            }
            var points = circuit.OrderedPoints.Select(WorldToScreen).ToArray();
            var bodyRanges = CircuitAnalyzer.GetHeatingBodyRanges(circuit);
            var hasBodyRange = bodyRanges.Count > 0;
            if (hasBodyRange)
            {
                var bodySegments = bodyRanges
                    .SelectMany(range => Enumerable.Range(range.StartIndex, range.EndIndex - range.StartIndex))
                    .ToHashSet();
                using var transitUnderlay = new Pen(Color.FromArgb(220, 4, 18, 24), selected ? 7 : 5)
                    { LineJoin = LineJoin.Round, StartCap = LineCap.Round, EndCap = LineCap.Round };
                using var transit = new Pen(selected ? Color.FromArgb(253, 224, 71) : ColorTranslator.FromHtml(circuit.Color), selected ? 4 : 1.8f)
                    { LineJoin = LineJoin.Round, StartCap = LineCap.Round, EndCap = LineCap.Round, DashStyle = DashStyle.Dash };
                using var bodyPen = new Pen(selected ? Color.FromArgb(253, 224, 71) : ColorTranslator.FromHtml(circuit.Color), selected ? 6 : 3)
                    { LineJoin = LineJoin.Round, StartCap = LineCap.Round, EndCap = LineCap.Round };

                void DrawRun(int firstSegmentIndex, int segmentCount, bool isBody)
                {
                    var run = points.Skip(firstSegmentIndex).Take(segmentCount + 1).ToArray();
                    if (isBody) g.DrawLines(bodyPen, run);
                    else { g.DrawLines(transitUnderlay, run); g.DrawLines(transit, run); }
                }

                var firstSegment = 0;
                var bodyRun = bodySegments.Contains(0);
                for (var segmentIndex = 1; segmentIndex < points.Length - 1; segmentIndex++)
                {
                    var nextBodyRun = bodySegments.Contains(segmentIndex);
                    if (nextBodyRun == bodyRun) continue;
                    DrawRun(firstSegment, segmentIndex - firstSegment, bodyRun);
                    firstSegment = segmentIndex;
                    bodyRun = nextBodyRun;
                }
                DrawRun(firstSegment, points.Length - 1 - firstSegment, bodyRun);
                continue;
            }
            if (serviceLayer)
            {
                using var underlay = new Pen(Color.FromArgb(215, 4, 18, 24), selected ? 8 : 6) { LineJoin = LineJoin.Round, StartCap = LineCap.Round, EndCap = LineCap.Round };
                g.DrawLines(underlay, points);
            }
            using var pen = new Pen(selected ? Color.FromArgb(253, 224, 71) : ColorTranslator.FromHtml(circuit.Color), selected ? 6 : serviceLayer ? 2.2f : 3) { LineJoin = LineJoin.Round, StartCap = LineCap.Round, EndCap = LineCap.Round };
            if (circuit.RoutingLayer == "VERTICAL_RISER_PROJECTION") pen.DashStyle = DashStyle.Dot;
            g.DrawLines(pen, points);
        }
    }

    private void Draw3DRouteMarkers(Graphics g)
    {
        var visibleCircuits = _project.Circuits.Where(IsCircuitVisible).ToArray();
        if (!visibleCircuits.Any(circuit => circuit.AxisElevationMm is not null || circuit.VerticalTransitions.Count > 0 ||
                                             circuit.OrderedPoints.Any(point => point.Z is not null))) return;
        var visibleIds = visibleCircuits.Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var analyses = GetCachedAnalyses().Where(item => visibleIds.Contains(item.CircuitId)).ToArray();
        var transitionCount = analyses.Sum(item => item.VerticalTransitions.Count);
        var showRampLabels = transitionCount <= 8 || _zoom >= 0.12f;
        using var markerFont = new Font("Segoe UI Semibold", 7.5f);
        using var rampPen = new Pen(Color.FromArgb(250, 34, 211, 238), 2);
        using var rampFill = new SolidBrush(Color.FromArgb(225, 8, 47, 73));
        using var rampText = new SolidBrush(Color.FromArgb(207, 250, 254));
        foreach (var transition in analyses.SelectMany(item => item.VerticalTransitions))
        {
            var transitionMidpointAlong = transition.StartTangentLengthMm + transition.RequiredArcProjectionMm / 2;
            var transitionFraction = transition.PlanProjectionMm <= 0.001 ? .5 : transitionMidpointAlong / transition.PlanProjectionMm;
            var midpoint = WorldToScreen(new PointMm(
                (int)Math.Round(transition.Start.X + (transition.End.X - transition.Start.X) * transitionFraction, MidpointRounding.AwayFromZero),
                (int)Math.Round(transition.Start.Y + (transition.End.Y - transition.Start.Y) * transitionFraction, MidpointRounding.AwayFromZero)));
            var diamond = new[]
            {
                new PointF(midpoint.X, midpoint.Y - 6),
                new PointF(midpoint.X + 6, midpoint.Y),
                new PointF(midpoint.X, midpoint.Y + 6),
                new PointF(midpoint.X - 6, midpoint.Y),
            };
            g.FillPolygon(rampFill, diamond);
            g.DrawPolygon(transition.MaterializedPass ? rampPen : Pens.OrangeRed, diamond);
            if (showRampLabels)
            {
                var label = transition.MaterializedPass
                    ? $"S-R{transition.RadiusMm:0}  Z{transition.Start.Z:0}→{transition.End.Z:0}"
                    : $"S-переход: REWORK";
                DrawMarkerLabel(g, markerFont, rampText, label, midpoint.X + 8, midpoint.Y - 8);
            }
        }

        using var errorFill = new SolidBrush(Color.FromArgb(235, 127, 29, 29));
        using var errorText = new SolidBrush(Color.FromArgb(254, 226, 226));
        foreach (var circuit in visibleCircuits)
        {
            var transitionSegments = circuit.VerticalTransitions.Select(item => item.SegmentIndex).ToHashSet();
            for (var segmentIndex = 0; segmentIndex + 1 < circuit.OrderedPoints.Count; segmentIndex++)
            {
                var start = CircuitAnalyzer.ResolvePoint3(circuit, circuit.OrderedPoints[segmentIndex]);
                var end = CircuitAnalyzer.ResolvePoint3(circuit, circuit.OrderedPoints[segmentIndex + 1]);
                if (Math.Abs(start.Z - end.Z) <= 0.001 || transitionSegments.Contains(segmentIndex)) continue;
                var marker = WorldToScreen(new PointMm(
                    (circuit.OrderedPoints[segmentIndex].X + circuit.OrderedPoints[segmentIndex + 1].X) / 2,
                    (circuit.OrderedPoints[segmentIndex].Y + circuit.OrderedPoints[segmentIndex + 1].Y) / 2));
                g.FillEllipse(errorFill, marker.X - 7, marker.Y - 7, 14, 14);
                g.DrawString("!", markerFont, Brushes.White, marker.X - 2.5f, marker.Y - 6.5f);
                DrawMarkerLabel(g, markerFont, errorText, "Z без S-перехода", marker.X + 8, marker.Y - 8);
            }
        }

        using var stackPen = new Pen(Color.FromArgb(245, 167, 139, 250), 2);
        using var stackInner = new Pen(Color.FromArgb(245, 45, 212, 191), 2);
        using var stackText = new SolidBrush(Color.FromArgb(237, 233, 254));
        var seenStacks = new HashSet<string>(StringComparer.Ordinal);
        var uniqueStacks = new List<StackCrossingDetail>();
        foreach (var analysis in analyses)
        foreach (var stack in analysis.StackCrossings.Where(item => visibleIds.Contains(item.OtherCircuitId)))
        {
            var firstId = string.CompareOrdinal(analysis.CircuitId, stack.OtherCircuitId) <= 0 ? analysis.CircuitId : stack.OtherCircuitId;
            var secondId = firstId == analysis.CircuitId ? stack.OtherCircuitId : analysis.CircuitId;
            var key = $"{firstId}|{secondId}|{stack.Position.X}|{stack.Position.Y}";
            if (!seenStacks.Add(key)) continue;
            uniqueStacks.Add(stack);
        }
        var showStackLabels = uniqueStacks.Count <= 6 || _zoom >= 0.12f;
        var stackRadius = _zoom < 0.06f ? 3f : _zoom < 0.12f ? 5f : 7f;
        var stackInnerRadius = Math.Max(1f, stackRadius * .42f);
        foreach (var stack in uniqueStacks)
        {
            var marker = WorldToScreen(stack.Position);
            g.DrawEllipse(stackPen, marker.X - stackRadius, marker.Y - stackRadius, stackRadius * 2, stackRadius * 2);
            g.DrawEllipse(stackInner, marker.X - stackInnerRadius, marker.Y - stackInnerRadius, stackInnerRadius * 2, stackInnerRadius * 2);
            if (showStackLabels)
                DrawMarkerLabel(g, markerFont, stackText,
                    $"STACK ΔZ {stack.AxisClearanceMm:0.#} · зазор {stack.SurfaceClearanceMm:0.#}", marker.X + 9, marker.Y - 8);
        }

        Draw3DLegend(g, analyses.Any(item => item.VerticalTransitions.Count > 0),
            seenStacks.Count > 0, analyses.Any(item => item.UnmaterializedElevationChangeCount > 0));
    }

    private static void DrawMarkerLabel(Graphics g, Font font, Brush brush, string text, float x, float y)
    {
        var size = g.MeasureString(text, font);
        using var background = new SolidBrush(Color.FromArgb(215, 4, 18, 24));
        g.FillRectangle(background, x - 2, y - 1, size.Width + 4, size.Height + 2);
        g.DrawString(text, font, brush, x, y);
    }

    private static void Draw3DLegend(Graphics g, bool hasRamps, bool hasStacks, bool hasErrors)
    {
        var lines = new List<(string Symbol, string Text, Color Color)>();
        if (hasRamps) lines.Add(("◇", "S-R · две дуги и горизонтальные касательные", Color.FromArgb(34, 211, 238)));
        if (hasStacks) lines.Add(("◎", "STACK · трубы пересекаются в плане, разнесены по Z", Color.FromArgb(167, 139, 250)));
        if (hasErrors) lines.Add(("!", "Z REWORK · перепад высоты без материализованного перехода", Color.FromArgb(248, 113, 113)));
        if (lines.Count == 0) return;
        using var font = new Font("Segoe UI", 8f, FontStyle.Bold);
        var width = lines.Max(item => g.MeasureString($"{item.Symbol}  {item.Text}", font).Width) + 16;
        var height = lines.Count * 20 + 10;
        using var background = new SolidBrush(Color.FromArgb(225, 4, 18, 24));
        using var border = new Pen(Color.FromArgb(100, 148, 163, 184), 1);
        g.FillRectangle(background, 10, 10, width, height);
        g.DrawRectangle(border, 10, 10, width, height);
        for (var index = 0; index < lines.Count; index++)
        {
            using var brush = new SolidBrush(lines[index].Color);
            g.DrawString($"{lines[index].Symbol}  {lines[index].Text}", font, brush, 18, 15 + index * 20);
        }
    }

    private IReadOnlyList<CircuitAnalysis> GetCachedAnalyses() =>
        _analysisCache ??= _project.Circuits.Select(circuit => CircuitAnalyzer.Analyze(_project, circuit)).ToArray();

    private bool IsCircuitVisible(ManualCircuit circuit)
    {
        if (!circuit.VisibleOnPlan) return false;
        if (!IsCircuitOnActiveFloor(circuit)) return false;
        var serviceLayer = circuit.RoutingLayer != "HEATING_PLANE";
        return serviceLayer ? ShowServiceCircuits : ShowHeatingCircuits;
    }

    private void DrawEngineeringDiagnostics(Graphics g)
    {
        var visibleIds = _project.Circuits.Where(IsCircuitVisible).Select(item => item.Id).ToHashSet(StringComparer.Ordinal);
        var analyses = GetCachedAnalyses().Where(item => visibleIds.Contains(item.CircuitId)).ToArray();
        var usefulSpanDetails = analyses
            .SelectMany(item => item.ExteriorWallBandUsefulSpanDetails)
            .GroupBy(item => (item.RoomId, item.WallId, item.LaneIndex))
            .Select(group => group.First())
            .ToArray();
        var usefulSpanKeys = usefulSpanDetails
            .Select(item => (item.RoomId, item.WallId, item.LaneIndex))
            .ToHashSet();
        var rawOnlyBandDetails = analyses
            .SelectMany(item => item.ExteriorWallBandCoverageDetails)
            .GroupBy(item => (item.RoomId, item.WallId, item.LaneIndex))
            .Select(group => group.First())
            .Where(item => !usefulSpanKeys.Contains((item.RoomId, item.WallId, item.LaneIndex)));
        using var bandFont = new Font("Segoe UI Semibold", 8);
        foreach (var detail in usefulSpanDetails)
        {
            var color = detail.UsefulSpanPass ? Color.FromArgb(185, 45, 212, 191) : Color.FromArgb(235, 248, 113, 113);
            using var pen = new Pen(color, detail.UsefulSpanPass ? 2.1f : 2.5f)
                { DashStyle = detail.UsefulSpanPass ? DashStyle.Solid : DashStyle.Dash };
            foreach (var interval in detail.EffectiveRequiredIntervals)
                g.DrawLine(pen, WorldToScreen(interval.Start), WorldToScreen(interval.End));
            if (detail.UsefulSpanPass || detail.EffectiveRequiredIntervals.Count == 0) continue;
            var first = detail.EffectiveRequiredIntervals[0];
            var last = detail.EffectiveRequiredIntervals[^1];
            var start = WorldToScreen(first.Start);
            var end = WorldToScreen(last.End);
            var midpoint = new PointF((start.X + end.X) / 2f, (start.Y + end.Y) / 2f);
            using var background = new SolidBrush(Color.FromArgb(220, 43, 15, 20));
            using var brush = new SolidBrush(Color.FromArgb(254, 202, 202));
            var label = $"3×100 useful L{detail.LaneIndex}: {detail.CoveragePercent:0.#}%";
            var size = g.MeasureString(label, bandFont);
            g.FillRectangle(background, midpoint.X - size.Width / 2 - 2, midpoint.Y - size.Height / 2 - 1, size.Width + 4, size.Height + 2);
            g.DrawString(label, bandFont, brush, midpoint.X - size.Width / 2, midpoint.Y - size.Height / 2);
        }

        foreach (var detail in rawOnlyBandDetails)
        {
            var color = detail.CoveragePass ? Color.FromArgb(165, 45, 212, 191) : Color.FromArgb(235, 248, 113, 113);
            using var pen = new Pen(color, detail.CoveragePass ? 1.5f : 2.5f) { DashStyle = DashStyle.Dash };
            var start = WorldToScreen(detail.TargetStart);
            var end = WorldToScreen(detail.TargetEnd);
            g.DrawLine(pen, start, end);
            if (detail.CoveragePass) continue;
            var midpoint = new PointF((start.X + end.X) / 2f, (start.Y + end.Y) / 2f);
            using var background = new SolidBrush(Color.FromArgb(220, 43, 15, 20));
            using var brush = new SolidBrush(Color.FromArgb(254, 202, 202));
            var label = $"3×100 L{detail.LaneIndex}: {detail.CoveragePercent:0.#}%";
            var size = g.MeasureString(label, bandFont);
            g.FillRectangle(background, midpoint.X - size.Width / 2 - 2, midpoint.Y - size.Height / 2 - 1, size.Width + 4, size.Height + 2);
            g.DrawString(label, bandFont, brush, midpoint.X - size.Width / 2, midpoint.Y - size.Height / 2);
        }

        foreach (var analysis in analyses)
        {
            foreach (var violation in analysis.BendRadiusViolations)
            {
                var start = WorldToScreen(violation.Start);
                var end = WorldToScreen(violation.End);
                using var pen = new Pen(Color.FromArgb(235, 251, 146, 60), 7) { StartCap = LineCap.Round, EndCap = LineCap.Round };
                g.DrawLine(pen, start, end);
                using var marker = new Pen(Color.FromArgb(255, 254, 215, 170), 2);
                g.DrawEllipse(marker, start.X - 5, start.Y - 5, 10, 10);
                g.DrawEllipse(marker, end.X - 5, end.Y - 5, 10, 10);
            }
            foreach (var intrusion in analysis.HeatingBodyWallIntrusionDetails)
            {
                using var pen = new Pen(Color.FromArgb(235, 244, 114, 182), 8) { StartCap = LineCap.Round, EndCap = LineCap.Round };
                g.DrawLine(pen, WorldToScreen(intrusion.SegmentStart), WorldToScreen(intrusion.SegmentEnd));
            }
        }
    }

    private void DrawPending(Graphics g)
    {
        if (_pendingWallStart is not null)
        {
            var p = WorldToScreen(_pendingWallStart); using var pen = new Pen(Color.FromArgb(251, 191, 36), 2); g.DrawEllipse(pen, p.X - 7, p.Y - 7, 14, 14);
            if (_hoverPoint is not null)
            {
                pen.DashStyle = DashStyle.Dash;
                g.DrawLine(pen, p, WorldToScreen(ConstrainPoint(_pendingWallStart, _hoverPoint)));
            }
        }
        if (_pendingWindowStart is not null)
        {
            var p = WorldToScreen(_pendingWindowStart); using var pen = new Pen(Color.FromArgb(125, 211, 252), 4) { DashStyle = DashStyle.Dash };
            g.DrawEllipse(pen, p.X - 6, p.Y - 6, 12, 12);
            if (_hoverPoint is not null) g.DrawLine(pen, p, WorldToScreen(ConstrainPoint(_pendingWindowStart, _hoverPoint)));
        }
        if (_activeCircuit?.OrderedPoints.LastOrDefault() is { } last && _hoverPoint is not null)
        {
            using var preview = new Pen(ColorTranslator.FromHtml(_activeCircuit.Color), 2) { DashStyle = DashStyle.Dash };
            g.DrawLine(preview, WorldToScreen(last), WorldToScreen(ConstrainPoint(last, _hoverPoint)));
        }
    }

    private static readonly string[] Palette = ["#29B6F6", "#FF9238", "#AB7DF6", "#32D583", "#F97066", "#FDD835"];
}
