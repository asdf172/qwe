using System.Collections.Generic;
using UnityEngine;

namespace LargeScaleDrawingMachine {
[ExecuteAlways]
[DisallowMultipleComponent]
public sealed class LargeScaleDrawingMachineController : MonoBehaviour {
  [Header("Photo-derived proportions (metres)")]
  public float lowerMotorSpan = 4.80f;
  public Vector3 leftMotorPosition = new Vector3(-1.953f, 0.0f, -0.279f);
  public Vector3 centerMotorPosition = new Vector3(-1.953f, 0.0f, -0.279f);
  public Vector3 rightMotorPosition = new Vector3(1.953f, 0.0f, -0.279f);

  [Header("Motor discs and eccentric pins")]
  public float discRadius = 0.28f;
  public float discThickness = 0.055f;
  public float eccentricRadius = 0.215f;
  public float jointPinRadius = 0.035f;
  public float jointPinHeight = 0.16f;

  [Header("Aluminium strips")]
  public float stripWidth = 0.075f;
  public float stripThickness = 0.014f;
  public float stripMassPerMetre = 0.36f;
  public float visualLayerGap = 0.028f;

  [Header("Stepper drive")]
  public float maximumTorque = 38.0f;
  public float maximumSpeedDegPerSecond = 150.0f;
  public float accelerationDegPerSecondSquared = 360.0f;
  public float motorSpring = 950.0f;
  public float motorDamper = 55.0f;

  [Header("Joint physics")]
  public float linkAngularDrag = 0.16f;
  public float linkLinearDrag = 0.03f;
  public PhysicsMaterial lowFrictionJointMaterial;

  private const float DefaultDemoLeftFrequency = 0.41f;
  private const float DefaultDemoCenterFrequency = 0.67f;
  private const float DefaultDemoRightFrequency = 0.53f;

  [Header("Runtime demo drive")]
  public bool playDemoOnStart = true;
  public float demoLeftAmplitude = 180.0f;
  public float demoCenterAmplitude = 180.0f;
  public float demoRightAmplitude = 180.0f;
  public float demoLeftFrequency = DefaultDemoLeftFrequency;
  public float demoCenterFrequency = DefaultDemoCenterFrequency;
  public float demoRightFrequency = DefaultDemoRightFrequency;

  [Header("Runtime UI")]
  public bool showRuntimeMotorUi = true;
  public Color runtimeUiBackgroundColor = new Color(1.0f, 1.0f, 1.0f, 0.92f);
  public Color runtimeUiTextColor = new Color(0.08f, 0.08f, 0.08f, 1.0f);
  public float uiMinimumMotorSpeedDegPerSecond = 0.0f;
  public float uiMaximumMotorSpeedDegPerSecond = 360.0f;

  [Header("Scene view")]
  public bool forceWhiteCameraBackground = true;
  public Color sceneBackgroundColor = Color.white;

  [Header("Drawing canvas")]
  public bool enableDrawing = true;
  public float canvasSize = 1.05f;
  public float canvasRotationSpeed = 18.0f;
  public float minDrawPointDistance = 0.008f;
  public Color inkColor = new Color(0.04f, 0.04f, 0.035f, 1.0f);
  public bool drawComplexSpirographPattern = false;
  public float markerTraceScale = 1.0f;
  public float complexPatternRadius = 0.525f;
  public float complexPatternSecondaryRadius = 0.21f;
  public float complexPatternSpeed = 0.33f;
  public int maxInkPoints = 16000;

  [Header("Runtime stability")]
  public bool preserveSceneLayoutOnPlay = true;
  public bool persistPlayModeLayout = false;
  public bool stabilizePhysicsOnBuild = true;
  public bool disableGeneratedColliders = true;
  public int solverIterations = 24;
  public int solverVelocityIterations = 12;

  [Header("Debug")]
  public bool debugMode = true;
  public Color motorAxisColor = Color.cyan;
  public Color hingePointColor = Color.yellow;
  public Color linkDebugColor = Color.white;

  private readonly List<LinkInfo> _links = new List<LinkInfo>();
  private readonly List<HingeJoint> _freeHinges = new List<HingeJoint>();
  private readonly List<MotorVisualFollower> _motorVisualFollowers =
      new List<MotorVisualFollower>();
  private readonly List<MotorAssembly> _motors = new List<MotorAssembly>();
  private MotorAssembly _leftMotor;
  private MotorAssembly _centerMotor;
  private MotorAssembly _rightMotor;
  private GameObject _markerHolder;
  private GameObject _markerTip;
  private GameObject _canvas;
  private LineRenderer _inkLine;
  private Vector3 _lastInkPoint;
  private bool _hasLastInkPoint;
  private bool _loadedPlayModeLayoutAfterExit;
  private bool _useSavedLayoutForNextBuild;
  private bool _savedPlayModeLayoutThisSession;
  private Texture2D _runtimeUiBackgroundTexture;
  private GUIStyle _runtimePanelStyle;
  private GUIStyle _runtimeTitleStyle;
  private GUIStyle _runtimeLabelStyle;
  private GUIStyle _runtimeToggleStyle;
  private GUIStyle _runtimeButtonStyle;

  [SerializeField, HideInInspector]
  private bool _hasSavedLeftOuter;
  [SerializeField, HideInInspector]
  private bool _hasSavedTopApex;
  [SerializeField, HideInInspector]
  private bool _hasSavedRightOuter;
  [SerializeField, HideInInspector]
  private bool _hasSavedLowerLeftKnuckle;
  [SerializeField, HideInInspector]
  private bool _hasSavedLowerRightKnuckle;
  [SerializeField, HideInInspector]
  private bool _hasSavedLeftMotorVisual;
  [SerializeField, HideInInspector]
  private bool _hasSavedCenterMotorVisual;
  [SerializeField, HideInInspector]
  private bool _hasSavedRightMotorVisual;
  [SerializeField, HideInInspector]
  private bool _hasSavedMarkerNode;
  [SerializeField, HideInInspector]
  private Vector3 _savedLeftOuter;
  [SerializeField, HideInInspector]
  private Vector3 _savedTopApex;
  [SerializeField, HideInInspector]
  private Vector3 _savedRightOuter;
  [SerializeField, HideInInspector]
  private Vector3 _savedLowerLeftKnuckle;
  [SerializeField, HideInInspector]
  private Vector3 _savedLowerRightKnuckle;
  [SerializeField, HideInInspector]
  private Vector3 _savedLeftMotorVisual;
  [SerializeField, HideInInspector]
  private Vector3 _savedCenterMotorVisual;
  [SerializeField, HideInInspector]
  private Vector3 _savedRightMotorVisual;
  [SerializeField, HideInInspector]
  private Vector3 _savedMarkerNode;

  public void SetLeftMotorAngle(float angle) => SetMotorTarget(_leftMotor, angle);
  public void SetCenterMotorAngle(float angle) => SetMotorTarget(_centerMotor, angle);
  public void SetRightMotorAngle(float angle) => SetMotorTarget(_rightMotor, angle);

  public void SetMotorAngles(float left, float center, float right) {
    SetLeftMotorAngle(left);
    SetCenterMotorAngle(center);
    SetRightMotorAngle(right);
  }

  private void Awake() {
    if (_motors.Count != 0)
      return;
    if (Application.isPlaying && preserveSceneLayoutOnPlay &&
        transform.childCount > 0 && BindExistingMachine())
      return;
    if (!Application.isPlaying && persistPlayModeLayout &&
        !_loadedPlayModeLayoutAfterExit && TryLoadPlayModeLayout()) {
      _loadedPlayModeLayoutAfterExit = true;
      _useSavedLayoutForNextBuild = true;
      BuildMachine();
      _useSavedLayoutForNextBuild = false;
      ClearPlayModeLayout();
      return;
    }
    BuildMachine();
  }

  private void OnEnable() {
    if (Application.isPlaying) {
      _savedPlayModeLayoutThisSession = false;
      return;
    }

    _loadedPlayModeLayoutAfterExit = false;
    if (!persistPlayModeLayout) {
      ClearSavedLayout();
      ClearPlayModeLayout();
      _useSavedLayoutForNextBuild = true;
      BuildMachine();
      _useSavedLayoutForNextBuild = false;
    }
  }

  private void Update() {
    if (Application.isPlaying)
      return;
    if (persistPlayModeLayout && !_loadedPlayModeLayoutAfterExit &&
        TryLoadPlayModeLayout()) {
      _loadedPlayModeLayoutAfterExit = true;
      _useSavedLayoutForNextBuild = true;
      BuildMachine();
      _useSavedLayoutForNextBuild = false;
      ClearPlayModeLayout();
      return;
    }
    if (transform.childCount == 0 || !persistPlayModeLayout)
      return;
    SaveEditorLayout(CaptureLayoutOverrides());
  }

  private void LateUpdate() {
    ApplyCameraBackground();
    UpdateMotorVisualFollowers();
  }
  private void OnDisable() => SavePlayModeLayoutIfNeeded();
  private void OnApplicationQuit() => SavePlayModeLayoutIfNeeded();
  private void OnDestroy() => SavePlayModeLayoutIfNeeded();

  private void SavePlayModeLayoutIfNeeded() {
    if (!Application.isPlaying || !persistPlayModeLayout ||
        _savedPlayModeLayoutThisSession)
      return;

    SavePlayModeLayout(CaptureLayoutOverrides());
    _savedPlayModeLayoutThisSession = true;
  }

  [ContextMenu("Reset saved layout and rebuild")]
  public void ResetSavedLayoutAndRebuild() {
    ClearSavedLayout();
    ClearPlayModeLayout();
    _useSavedLayoutForNextBuild = true;
    BuildMachine();
    _useSavedLayoutForNextBuild = false;
  }

  [ContextMenu("Rebuild physical machine")]
  public void BuildMachine() {
    LayoutOverrides layoutOverrides =
        _useSavedLayoutForNextBuild ? default : CaptureLayoutOverrides();
    ClearChildren();
    _links.Clear();
    _freeHinges.Clear();
    _motorVisualFollowers.Clear();
    _motors.Clear();
    CreateMaterialsIfNeeded();

    Vector3 defaultLeftOuter = new Vector3(-3.05f, 0.0f, 0.70f);
    Vector3 defaultTopApex = new Vector3(0.0f, 0.0f, 2.02f);
    Vector3 defaultRightOuter = new Vector3(3.05f, 0.0f, 0.70f);
    Vector3 defaultLowerLeftKnuckle = new Vector3(-1.05f, 0.0f, -0.72f);
    Vector3 defaultLowerRightKnuckle = new Vector3(1.05f, 0.0f, -0.72f);
    Vector3 defaultLeftMotorVisual = new Vector3(-1.953f, 0.0f, -0.279f);
    Vector3 defaultCenterMotorVisual = new Vector3(-1.953f, 0.0f, -0.279f);
    Vector3 defaultRightMotorVisual = new Vector3(1.953f, 0.0f, -0.279f);
    Vector3 defaultMarkerNode = new Vector3(0.0f, 0.0f, 0.26f);

    Vector3 leftOuter = ResolveLayoutPosition(layoutOverrides.LeftOuter,
        _hasSavedLeftOuter, _savedLeftOuter, defaultLeftOuter);
    Vector3 rightOuter = ResolveLayoutPosition(layoutOverrides.RightOuter,
        _hasSavedRightOuter, _savedRightOuter, defaultRightOuter);
    Vector3 leftMotorVisual = ResolveLayoutPosition(layoutOverrides.LeftMotorVisual,
        _hasSavedLeftMotorVisual, _savedLeftMotorVisual, defaultLeftMotorVisual);
    Vector3 centerMotorVisual = ResolveLayoutPosition(
        layoutOverrides.CenterMotorVisual, _hasSavedCenterMotorVisual,
        _savedCenterMotorVisual, defaultCenterMotorVisual);
    Vector3 rightMotorVisual = ResolveLayoutPosition(
        layoutOverrides.RightMotorVisual, _hasSavedRightMotorVisual,
        _savedRightMotorVisual, defaultRightMotorVisual);
    Vector3 topApex = ResolveLayoutPosition(layoutOverrides.TopApex,
        _hasSavedTopApex, _savedTopApex, defaultTopApex);
    Vector3 lowerLeftKnuckle = ResolveLayoutPosition(
        layoutOverrides.LowerLeftKnuckle, _hasSavedLowerLeftKnuckle,
        _savedLowerLeftKnuckle,
        defaultLowerLeftKnuckle + (leftMotorVisual - defaultLeftMotorVisual));
    Vector3 lowerRightKnuckle = ResolveLayoutPosition(
        layoutOverrides.LowerRightKnuckle, _hasSavedLowerRightKnuckle,
        _savedLowerRightKnuckle,
        defaultLowerRightKnuckle + (rightMotorVisual - defaultRightMotorVisual));
    Vector3 markerNode = ResolveLayoutPosition(layoutOverrides.MarkerNode,
        _hasSavedMarkerNode, _savedMarkerNode, defaultMarkerNode);

    _leftMotor = CreateMotorWithPinAt("Left stepper", lowerLeftKnuckle,
                                      leftMotorVisual, -65.0f,
                                      ref leftMotorPosition);
    _centerMotor = CreateMotorWithPinAt("Center stepper / marker node", topApex,
                                        centerMotorVisual, -90.0f,
                                        ref centerMotorPosition);
    _rightMotor = CreateMotorWithPinAt("Right stepper", lowerRightKnuckle,
                                       rightMotorVisual, -115.0f,
                                       ref rightMotorPosition);

    GameObject leftOuterPin = CreatePassivePin("Left outer corner bolt",
                                               leftOuter, 0.18f);
    GameObject topPin = _centerMotor.PinBody;
    GameObject rightOuterPin = CreatePassivePin("Right outer corner bolt",
                                                rightOuter, 0.18f);
    GameObject leftKnuckle = _leftMotor.PinBody;
    GameObject rightKnuckle = _rightMotor.PinBody;
    GameObject markerPin = CreateMarkerHolder(markerNode);

    CreateLink("left top outer aluminium strip", leftOuterPin, topPin, 0);
    CreateLink("right top outer aluminium strip", topPin, rightOuterPin, 0);
    CreateLink("left one-piece motor side strip", leftOuterPin, leftKnuckle, 0);
    CreateLink("right one-piece motor side strip", rightOuterPin, rightKnuckle, 0);
    CreateLink("left inner diagonal to marker", leftKnuckle, markerPin, 0);
    CreateLink("right inner diagonal to marker", rightKnuckle, markerPin, 0);
    CreateDrawingCanvas();
  }

  private void ClearSavedLayout() {
    _hasSavedLeftOuter = _hasSavedTopApex = _hasSavedRightOuter =
        _hasSavedLowerLeftKnuckle = _hasSavedLowerRightKnuckle = false;
    _hasSavedLeftMotorVisual = _hasSavedCenterMotorVisual =
        _hasSavedRightMotorVisual = _hasSavedMarkerNode = false;
    _savedLeftOuter = _savedTopApex = _savedRightOuter =
        _savedLowerLeftKnuckle = _savedLowerRightKnuckle = Vector3.zero;
    _savedLeftMotorVisual = _savedCenterMotorVisual = _savedRightMotorVisual =
        _savedMarkerNode = Vector3.zero;
    leftMotorPosition = new Vector3(-1.953f, 0.0f, -0.279f);
    centerMotorPosition = new Vector3(-1.953f, 0.0f, -0.279f);
    rightMotorPosition = new Vector3(1.953f, 0.0f, -0.279f);
  }

  private bool BindExistingMachine() {
    _links.Clear();
    _freeHinges.Clear();
    _motorVisualFollowers.Clear();
    _motors.Clear();
    _leftMotor = BindExistingMotor("Left stepper");
    _centerMotor = BindExistingMotor("Center stepper / marker node");
    _rightMotor = BindExistingMotor("Right stepper");
    if (_leftMotor == null || _centerMotor == null || _rightMotor == null) {
      _links.Clear();
      _freeHinges.Clear();
      _motorVisualFollowers.Clear();
      _motors.Clear();
      return false;
    }
    BindExistingMotorVisual(_leftMotor,
        "Left stepper visible motor moved to side rail", false);
    BindExistingMotorVisual(_centerMotor,
        "Center stepper / marker node visible motor moved to side rail", true);
    BindExistingMotorVisual(_rightMotor,
        "Right stepper visible motor moved to side rail", false);
    BindExistingLinks();
    BindExistingDrawingObjects();
    return true;
  }

  private MotorAssembly BindExistingMotor(string name) {
    Transform root = FindDeepChild(transform, name);
    Transform disc = FindDeepChild(transform,
        name + " black plywood-edged rotating disc");
    Transform pin = FindDeepChild(transform,
        name + " eccentric off-axis bolt");
    if (root == null || disc == null || pin == null)
      return null;
    Rigidbody discBody = disc.GetComponent<Rigidbody>();
    HingeJoint axisJoint = disc.GetComponent<HingeJoint>();
    Rigidbody pinBody = pin.GetComponent<Rigidbody>();
    if (discBody == null || axisJoint == null || pinBody == null)
      return null;
    var motor = new MotorAssembly(name, root.gameObject, disc.gameObject,
        discBody, axisJoint, pin.gameObject, pinBody) {
      DemoAngle = disc.localEulerAngles.y
    };
    _motors.Add(motor);
    return motor;
  }

  private void BindExistingMotorVisual(MotorAssembly motor, string shellName,
                                       bool followPinPosition) {
    Transform shell = FindDeepChild(transform, shellName);
    Transform visualDisc = FindDeepChild(transform,
        shellName + " black plywood-edged disc visual");
    Transform visualPin = FindDeepChild(transform,
        shellName + " eccentric pin visual follower");
    if (shell == null || visualDisc == null)
      return;
    _motorVisualFollowers.Add(new MotorVisualFollower(
        motor.Disc.transform, motor.PinBody.transform, shell, visualDisc,
        visualPin, followPinPosition));
  }

  private void BindExistingLinks() {
    foreach (HingeJoint hinge in GetComponentsInChildren<HingeJoint>())
      if (hinge.name.EndsWith(" hinge", System.StringComparison.Ordinal))
        _freeHinges.Add(hinge);
    BindExistingLink("left top outer aluminium strip");
    BindExistingLink("right top outer aluminium strip");
    BindExistingLink("left one-piece motor side strip");
    BindExistingLink("right one-piece motor side strip");
    BindExistingLink("left inner diagonal to marker");
    BindExistingLink("right inner diagonal to marker");
  }

  private void BindExistingLink(string name) {
    Transform link = FindDeepChild(transform, name);
    if (link == null)
      return;
    Rigidbody body = link.GetComponent<Rigidbody>();
    if (body == null)
      return;
    _links.Add(new LinkInfo(name, link.localScale.z, body));
  }

  private void BindExistingDrawingObjects() {
    Transform markerTip = FindDeepChild(transform, "marker drawing tip");
    Transform canvas = FindDeepChild(transform,
        "rotating square drawing canvas pivot");
    Transform inkLine = FindDeepChild(transform, "generated ink line");
    _markerTip = markerTip != null ? markerTip.gameObject : null;
    _canvas = canvas != null ? canvas.gameObject : null;
    _inkLine = inkLine != null ? inkLine.GetComponent<LineRenderer>() : null;
    _hasLastInkPoint = _inkLine != null && _inkLine.positionCount > 0;
    if (_hasLastInkPoint)
      _lastInkPoint = _inkLine.GetPosition(_inkLine.positionCount - 1);
  }

  private MotorAssembly CreateMotorWithPinAt(string name,
                                             Vector3 desiredPinPosition,
                                             Vector3 visibleMotorPosition,
                                             float initialAngle,
                                             ref Vector3 storedMotorPosition) {
    Vector3 eccentricOffset = Quaternion.Euler(0.0f, initialAngle, 0.0f) *
                              new Vector3(eccentricRadius, 0.08f, 0.0f);
    Vector3 motorCenterPosition = desiredPinPosition -
        new Vector3(eccentricOffset.x, 0.0f, eccentricOffset.z);
    MotorAssembly motor = CreateMotor(name, motorCenterPosition, initialAngle);
    bool isCenterMotor = name.StartsWith("Center", System.StringComparison.Ordinal);
    if (!isCenterMotor)
      HideDriveMotorBodyRenderers(motor);
    MotorVisualShell shell = CreateCenteredMotorShell(
        name + " visible motor moved to side rail", visibleMotorPosition,
        initialAngle, isCenterMotor);
    if (!isCenterMotor && shell.Pin != null)
      shell.Pin.gameObject.SetActive(false);
    _motorVisualFollowers.Add(new MotorVisualFollower(
        motor.Disc.transform, motor.PinBody.transform, shell.Root, shell.Disc,
        shell.Pin, isCenterMotor));
    storedMotorPosition = visibleMotorPosition;
    return motor;
  }

  private static Vector3 ResolveLayoutPosition(
      Vector3? capturedPosition, bool hasSavedPosition, Vector3 savedPosition,
      Vector3 defaultPosition) => capturedPosition.HasValue
                                      ? capturedPosition.Value
                                  : hasSavedPosition ? savedPosition
                                                     : defaultPosition;

  private void SaveEditorLayout(LayoutOverrides layoutOverrides) {
    SaveLayoutPosition(layoutOverrides.LeftOuter, ref _hasSavedLeftOuter,
                       ref _savedLeftOuter);
    SaveLayoutPosition(layoutOverrides.TopApex, ref _hasSavedTopApex,
                       ref _savedTopApex);
    SaveLayoutPosition(layoutOverrides.RightOuter, ref _hasSavedRightOuter,
                       ref _savedRightOuter);
    SaveLayoutPosition(layoutOverrides.LowerLeftKnuckle,
                       ref _hasSavedLowerLeftKnuckle,
                       ref _savedLowerLeftKnuckle);
    SaveLayoutPosition(layoutOverrides.LowerRightKnuckle,
                       ref _hasSavedLowerRightKnuckle,
                       ref _savedLowerRightKnuckle);
    SaveLayoutPosition(layoutOverrides.LeftMotorVisual,
                       ref _hasSavedLeftMotorVisual, ref _savedLeftMotorVisual);
    SaveLayoutPosition(layoutOverrides.CenterMotorVisual,
                       ref _hasSavedCenterMotorVisual, ref _savedCenterMotorVisual);
    SaveLayoutPosition(layoutOverrides.RightMotorVisual,
                       ref _hasSavedRightMotorVisual, ref _savedRightMotorVisual);
    SaveLayoutPosition(layoutOverrides.MarkerNode, ref _hasSavedMarkerNode,
                       ref _savedMarkerNode);
  }

  private static void SaveLayoutPosition(Vector3? capturedPosition,
                                         ref bool hasSavedPosition,
                                         ref Vector3 savedPosition) {
    if (!capturedPosition.HasValue)
      return;
    savedPosition = capturedPosition.Value;
    hasSavedPosition = true;
  }

  private void SavePlayModeLayout(LayoutOverrides layoutOverrides) {
    SaveEditorLayout(layoutOverrides);
    string key = LayoutPersistenceKey;
    PlayerPrefs.SetInt(key + "has", 1);
    SavePersistedLayoutPosition(key, "leftOuter", layoutOverrides.LeftOuter);
    SavePersistedLayoutPosition(key, "topApex", layoutOverrides.TopApex);
    SavePersistedLayoutPosition(key, "rightOuter", layoutOverrides.RightOuter);
    SavePersistedLayoutPosition(key, "lowerLeftKnuckle",
                                layoutOverrides.LowerLeftKnuckle);
    SavePersistedLayoutPosition(key, "lowerRightKnuckle",
                                layoutOverrides.LowerRightKnuckle);
    SavePersistedLayoutPosition(key, "leftMotorVisual",
                                layoutOverrides.LeftMotorVisual);
    SavePersistedLayoutPosition(key, "centerMotorVisual",
                                layoutOverrides.CenterMotorVisual);
    SavePersistedLayoutPosition(key, "rightMotorVisual",
                                layoutOverrides.RightMotorVisual);
    SavePersistedLayoutPosition(key, "markerNode", layoutOverrides.MarkerNode);
    PlayerPrefs.Save();
  }

  private bool TryLoadPlayModeLayout() {
    string key = LayoutPersistenceKey;
    if (PlayerPrefs.GetInt(key + "has", 0) == 0)
      return false;
    LoadPersistedLayoutPosition(key, "leftOuter", ref _hasSavedLeftOuter,
                                ref _savedLeftOuter);
    LoadPersistedLayoutPosition(key, "topApex", ref _hasSavedTopApex,
                                ref _savedTopApex);
    LoadPersistedLayoutPosition(key, "rightOuter", ref _hasSavedRightOuter,
                                ref _savedRightOuter);
    LoadPersistedLayoutPosition(key, "lowerLeftKnuckle",
                                ref _hasSavedLowerLeftKnuckle,
                                ref _savedLowerLeftKnuckle);
    LoadPersistedLayoutPosition(key, "lowerRightKnuckle",
                                ref _hasSavedLowerRightKnuckle,
                                ref _savedLowerRightKnuckle);
    LoadPersistedLayoutPosition(key, "leftMotorVisual",
                                ref _hasSavedLeftMotorVisual,
                                ref _savedLeftMotorVisual);
    LoadPersistedLayoutPosition(key, "centerMotorVisual",
                                ref _hasSavedCenterMotorVisual,
                                ref _savedCenterMotorVisual);
    LoadPersistedLayoutPosition(key, "rightMotorVisual",
                                ref _hasSavedRightMotorVisual,
                                ref _savedRightMotorVisual);
    LoadPersistedLayoutPosition(key, "markerNode", ref _hasSavedMarkerNode,
                                ref _savedMarkerNode);
    return true;
  }

  private void ClearPlayModeLayout() {
    string key = LayoutPersistenceKey;
    PlayerPrefs.DeleteKey(key + "has");
  }

  private string LayoutPersistenceKey =>
      "LargeScaleDrawingMachineController." + gameObject.scene.path + "." +
      transform.GetSiblingIndex() + "." + name + ".";

  private static void SavePersistedLayoutPosition(string key, string name,
                                                  Vector3? position) {
    PlayerPrefs.SetInt(key + name + ".has", position.HasValue ? 1 : 0);
    if (!position.HasValue)
      return;
    PlayerPrefs.SetFloat(key + name + ".x", position.Value.x);
    PlayerPrefs.SetFloat(key + name + ".y", position.Value.y);
    PlayerPrefs.SetFloat(key + name + ".z", position.Value.z);
  }

  private static void LoadPersistedLayoutPosition(string key, string name,
                                                  ref bool hasSavedPosition,
                                                  ref Vector3 savedPosition) {
    if (PlayerPrefs.GetInt(key + name + ".has", 0) == 0)
      return;
    savedPosition = new Vector3(PlayerPrefs.GetFloat(key + name + ".x"),
                                PlayerPrefs.GetFloat(key + name + ".y"),
                                PlayerPrefs.GetFloat(key + name + ".z"));
    hasSavedPosition = true;
  }

  private LayoutOverrides CaptureLayoutOverrides() => new LayoutOverrides(
      GetExistingPlanarPosition("Left outer corner bolt"),
      GetFirstExistingPlanarPosition(
          "Center stepper / marker node visible motor moved to side rail",
          "Center stepper / marker node visible motor moved to side rail " +
              "black motor body visual",
          "Center stepper / marker node visible motor moved to side rail " +
              "black plywood-edged disc visual"),
      GetExistingPlanarPosition("Right outer corner bolt"),
      GetExistingPlanarPosition("Left stepper eccentric off-axis bolt"),
      GetExistingPlanarPosition("Right stepper eccentric off-axis bolt"),
      GetFirstExistingPlanarPosition(
          "Left stepper visible motor moved to side rail",
          "Left stepper visible motor moved to side rail black motor body " +
              "visual",
          "Left stepper visible motor moved to side rail black plywood-edged " +
              "disc visual"),
      GetFirstExistingPlanarPosition(
          "Center stepper / marker node visible motor moved to side rail",
          "Center stepper / marker node visible motor moved to side rail " +
              "black motor body visual",
          "Center stepper / marker node visible motor moved to side rail " +
              "black plywood-edged disc visual"),
      GetFirstExistingPlanarPosition(
          "Right stepper visible motor moved to side rail",
          "Right stepper visible motor moved to side rail black motor body " +
              "visual",
          "Right stepper visible motor moved to side rail black " +
              "plywood-edged disc visual"),
      GetExistingPlanarPosition("Central marker hinge stack"));

  private Vector3? GetExistingPlanarPosition(string objectName) {
    Transform existing = FindDeepChild(transform, objectName);
    if (existing == null)
      return null;
    Vector3 local = transform.InverseTransformPoint(existing.position);
    local.y = 0.0f;
    return local;
  }

  private Vector3? GetFirstExistingPlanarPosition(params string[] objectNames) {
    foreach (string objectName in objectNames) {
      Vector3? position = GetExistingPlanarPosition(objectName);
      if (position.HasValue)
        return position;
    }
    return null;
  }

  private static Transform FindDeepChild(Transform root, string objectName) {
    for (int i = 0; i < root.childCount; i++) {
      Transform child = root.GetChild(i);
      if (child.name == objectName)
        return child;
      Transform nested = FindDeepChild(child, objectName);
      if (nested != null)
        return nested;
    }
    return null;
  }

  private void HideDriveMotorBodyRenderers(MotorAssembly motor) {
    foreach (Renderer renderer in motor.Root.GetComponentsInChildren<Renderer>())
      renderer.enabled = false;
  }

  private MotorVisualShell CreateCenteredMotorShell(
      string name, Vector3 position, float initialAngle,
      bool centerVisualPinOnMotor) {
    var shell = new GameObject(name);
    shell.transform.SetParent(transform, false);
    shell.transform.localPosition = position;
    var baseBlock = GameObject.CreatePrimitive(PrimitiveType.Cube);
    baseBlock.name = name + " black motor body visual";
    baseBlock.transform.SetParent(shell.transform, false);
    baseBlock.transform.localScale = new Vector3(0.34f, 0.34f, 0.34f);
    baseBlock.transform.localPosition = new Vector3(0, 0.17f, 0);
    baseBlock.GetComponent<Renderer>().sharedMaterial = MotorMaterial;
    ConfigureGeneratedCollider(baseBlock);
    var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
    disc.name = name + " black plywood-edged disc visual";
    disc.transform.SetParent(shell.transform, false);
    disc.transform.localScale =
        new Vector3(discRadius * 2.0f, discThickness * 0.5f, discRadius * 2.0f);
    disc.transform.localPosition = new Vector3(0, 0.42f, 0);
    disc.transform.localRotation = Quaternion.Euler(0, initialAngle, 0);
    disc.GetComponent<Renderer>().sharedMaterial = DiscTopMaterial;
    ConfigureGeneratedCollider(disc);
    var pin = GameObject.CreatePrimitive(PrimitiveType.Sphere);
    pin.name = name + " eccentric pin visual follower";
    pin.transform.SetParent(shell.transform, false);
    pin.transform.localPosition =
        centerVisualPinOnMotor ? new Vector3(0.0f, 0.50f, 0.0f)
                               : new Vector3(eccentricRadius, 0.50f, 0.0f);
    pin.transform.localScale = Vector3.one * (jointPinRadius * 3.2f);
    pin.GetComponent<Renderer>().sharedMaterial = BoltMaterial;
    ConfigureGeneratedCollider(pin);
    return new MotorVisualShell(shell.transform, disc.transform, pin.transform);
  }

  private void UpdateMotorVisualFollowers() {
    foreach (MotorVisualFollower follower in _motorVisualFollowers) {
      if (follower.DriveDisc == null || follower.DrivePin == null ||
          follower.VisualRoot == null)
        continue;
      if (follower.VisualDisc != null)
        follower.VisualDisc.localRotation = follower.DriveDisc.localRotation;
      if (follower.FollowPinPosition && follower.VisualPin != null)
        follower.VisualPin.position = follower.DrivePin.position;
    }
  }

  private MotorAssembly CreateMotor(string name, Vector3 position,
                                    float initialAngle) {
    var root = new GameObject(name);
    root.transform.SetParent(transform, false);
    root.transform.localPosition = position;
    var baseBlock = GameObject.CreatePrimitive(PrimitiveType.Cube);
    baseBlock.name = name + " black motor body";
    baseBlock.transform.SetParent(root.transform, false);
    baseBlock.transform.localScale = new Vector3(0.34f, 0.34f, 0.34f);
    baseBlock.transform.localPosition = new Vector3(0, 0.17f, 0);
    baseBlock.GetComponent<Renderer>().sharedMaterial = MotorMaterial;
    var baseRb = baseBlock.AddComponent<Rigidbody>();
    baseRb.isKinematic = true;
    ConfigureGeneratedCollider(baseBlock);
    ConfigurePlanarBody(baseRb, true);
    var disc = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
    disc.name = name + " black plywood-edged rotating disc";
    disc.transform.SetParent(root.transform, false);
    disc.transform.localScale =
        new Vector3(discRadius * 2.0f, discThickness * 0.5f, discRadius * 2.0f);
    disc.transform.localPosition = new Vector3(0, 0.42f, 0);
    disc.transform.localRotation = Quaternion.Euler(0, initialAngle, 0);
    disc.GetComponent<Renderer>().sharedMaterial = DiscTopMaterial;
    var discRb = disc.AddComponent<Rigidbody>();
    discRb.mass = 0.42f;
    discRb.drag = 0.02f;
    discRb.angularDrag = 0.08f;
    ConfigureGeneratedCollider(disc);
    ConfigurePlanarBody(discRb, true);
    var hinge = disc.AddComponent<HingeJoint>();
    hinge.connectedBody = baseRb;
    hinge.axis = Vector3.up;
    hinge.anchor = Vector3.zero;
    hinge.enableCollision = false;
    hinge.enablePreprocessing = false;
    hinge.useLimits = false;
    hinge.useMotor = true;
    hinge.useSpring = true;
    ConfigureMotorJoint(hinge, initialAngle);
    var pin = CreatePinBody(
        name + " eccentric off-axis bolt",
        disc.transform.TransformPoint(new Vector3(eccentricRadius, 0.08f, 0)),
        0.16f);
    pin.transform.SetParent(root.transform, true);
    var fixedToDisc = pin.AddComponent<FixedJoint>();
    fixedToDisc.connectedBody = discRb;
    fixedToDisc.enableCollision = false;
    fixedToDisc.enablePreprocessing = false;
    var motor = new MotorAssembly(name, root, disc, discRb, hinge, pin,
        pin.GetComponent<Rigidbody>()) { DemoAngle = initialAngle };
    _motors.Add(motor);
    return motor;
  }

  private void ConfigureMotorJoint(HingeJoint hinge, float target) {
    var motor = hinge.motor;
    motor.force = maximumTorque;
    motor.targetVelocity = 0.0f;
    motor.freeSpin = false;
    hinge.motor = motor;
    var spring = hinge.spring;
    spring.spring = motorSpring;
    spring.damper = motorDamper;
    spring.targetPosition = Mathf.Repeat(target, 360.0f);
    hinge.spring = spring;
  }

  private void SetMotorTarget(MotorAssembly motor, float angle) {
    if (motor == null)
      return;
    motor.DiscBody.isKinematic = false;
    motor.PinRigidbody.isKinematic = false;
    motor.AxisJoint.useSpring = true;
    motor.AxisJoint.useMotor = true;
    var spring = motor.AxisJoint.spring;
    spring.targetPosition = Mathf.Repeat(angle, 360.0f);
    motor.AxisJoint.spring = spring;
    var jointMotor = motor.AxisJoint.motor;
    float delta = Mathf.DeltaAngle(motor.AxisJoint.angle, spring.targetPosition);
    float desiredVelocity = Mathf.Clamp(delta * 4.0f, -maximumSpeedDegPerSecond,
                                        maximumSpeedDegPerSecond);
    jointMotor.targetVelocity = Mathf.MoveTowards(
        jointMotor.targetVelocity, desiredVelocity,
        accelerationDegPerSecondSquared * Time.fixedDeltaTime);
    jointMotor.force = maximumTorque;
    motor.AxisJoint.motor = jointMotor;
  }

  private void SetMotorVelocity(MotorAssembly motor,
                                float targetVelocityDegPerSecond) {
    if (motor == null)
      return;
    motor.AxisJoint.useSpring = false;
    motor.AxisJoint.useMotor = true;
    var jointMotor = motor.AxisJoint.motor;
    float clampedVelocity = Mathf.Clamp(targetVelocityDegPerSecond,
        -maximumSpeedDegPerSecond, maximumSpeedDegPerSecond);
    jointMotor.targetVelocity = Mathf.MoveTowards(
        jointMotor.targetVelocity, clampedVelocity,
        accelerationDegPerSecondSquared * Time.fixedDeltaTime);
    jointMotor.force = maximumTorque;
    jointMotor.freeSpin = false;
    motor.AxisJoint.motor = jointMotor;
    DriveMotorKinematically(motor, jointMotor.targetVelocity);
  }

  private void DriveMotorKinematically(MotorAssembly motor,
                                       float velocityDegPerSecond) {
    motor.DiscBody.isKinematic = true;
    motor.PinRigidbody.isKinematic = true;
    motor.DemoAngle = Mathf.Repeat(
        motor.DemoAngle + velocityDegPerSecond * Time.fixedDeltaTime, 360.0f);
    Quaternion localRotation = Quaternion.Euler(0.0f, motor.DemoAngle, 0.0f);
    Quaternion worldRotation = motor.Root.transform.rotation * localRotation;
    Vector3 pinLocalPosition =
        localRotation * new Vector3(eccentricRadius, 0.08f, 0.0f);
    Vector3 pinWorldPosition = motor.Root.transform.TransformPoint(pinLocalPosition);
    motor.DiscBody.MoveRotation(worldRotation);
    motor.PinRigidbody.MovePosition(pinWorldPosition);
  }

  private void FixedUpdate() {
    if (playDemoOnStart) {
      SetMotorVelocity(_leftMotor, demoLeftFrequency * 360.0f);
      SetMotorVelocity(_centerMotor, demoCenterFrequency * 360.0f);
      SetMotorVelocity(_rightMotor, demoRightFrequency * 360.0f);
      UpdateDrawingCanvas();
      return;
    }
    foreach (var motor in _motors)
      SetMotorTarget(motor, motor.AxisJoint.spring.targetPosition);
    UpdateDrawingCanvas();
  }

  private void CreateLink(string name, GameObject aBody, GameObject bBody,
                          int layer) {
    Vector3 a = GetBodyHingePoint(aBody, layer);
    Vector3 b = GetBodyHingePoint(bBody, layer);
    Vector3 midpoint = (a + b) * 0.5f;
    Vector3 direction = b - a;
    float length = direction.magnitude;
    var link = GameObject.CreatePrimitive(PrimitiveType.Cube);
    link.name = name;
    link.transform.SetParent(transform, true);
    link.transform.position = midpoint;
    link.transform.rotation = Quaternion.LookRotation(direction.normalized,
                                                      Vector3.up);
    link.transform.localScale = new Vector3(stripWidth, stripThickness, length);
    link.GetComponent<Renderer>().sharedMaterial = AluminiumMaterial;
    var rb = link.AddComponent<Rigidbody>();
    rb.mass = Mathf.Max(0.04f, length * stripMassPerMetre);
    rb.drag = linkLinearDrag;
    rb.angularDrag = linkAngularDrag;
    ConfigureGeneratedCollider(link);
    ConfigurePlanarBody(rb, false);
    AddFreeHinge(link, aBody.GetComponent<Rigidbody>(),
                 link.transform.InverseTransformPoint(a),
                 aBody.transform.InverseTransformPoint(a), name + " A hinge");
    AddFreeHinge(link, bBody.GetComponent<Rigidbody>(),
                 link.transform.InverseTransformPoint(b),
                 bBody.transform.InverseTransformPoint(b), name + " B hinge");
    _links.Add(new LinkInfo(name, length, rb));
  }

  private Vector3 GetBodyHingePoint(GameObject body, int layer) {
    Vector3 point = body.transform.position;
    point.y += layer * visualLayerGap;
    return point;
  }

  private void AddFreeHinge(GameObject owner, Rigidbody connected,
                            Vector3 anchor, Vector3 connectedAnchor,
                            string name) {
    var hinge = owner.AddComponent<HingeJoint>();
    hinge.name = name;
    hinge.connectedBody = connected;
    hinge.axis = Vector3.up;
    hinge.anchor = anchor;
    hinge.connectedAnchor = connectedAnchor;
    hinge.autoConfigureConnectedAnchor = false;
    hinge.enableCollision = false;
    hinge.enablePreprocessing = false;
    hinge.massScale = 1.0f;
    hinge.connectedMassScale = 1.0f;
    hinge.useLimits = false;
    _freeHinges.Add(hinge);
  }

  private GameObject CreatePassivePin(string name, Vector3 position,
                                      float height) =>
      CreatePinBody(name, position + Vector3.up * 0.50f, height);

  private GameObject CreatePinBody(string name, Vector3 position, float height) {
    var pin = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
    pin.name = name;
    pin.transform.SetParent(transform, true);
    pin.transform.position = position;
    pin.transform.localScale = new Vector3(jointPinRadius * 2.0f,
                                           height * 0.5f,
                                           jointPinRadius * 2.0f);
    pin.GetComponent<Renderer>().sharedMaterial = BoltMaterial;
    var rb = pin.AddComponent<Rigidbody>();
    rb.mass = 0.08f;
    rb.drag = 0.02f;
    rb.angularDrag = 0.02f;
    ConfigureGeneratedCollider(pin);
    ConfigurePlanarBody(rb, false);
    return pin;
  }

  private void ConfigureGeneratedCollider(GameObject generatedObject) {
    if (!disableGeneratedColliders)
      return;
    var collider = generatedObject.GetComponent<Collider>();
    if (collider != null)
      collider.enabled = false;
  }

  private void ConfigurePlanarBody(Rigidbody rb, bool motorDiscOrBase) {
    if (!stabilizePhysicsOnBuild || rb == null)
      return;
    rb.useGravity = false;
    rb.interpolation = RigidbodyInterpolation.Interpolate;
    rb.collisionDetectionMode = CollisionDetectionMode.Discrete;
    rb.solverIterations = solverIterations;
    rb.solverVelocityIterations = solverVelocityIterations;
    rb.maxAngularVelocity = maximumSpeedDegPerSecond * Mathf.Deg2Rad * 2.0f;
    rb.constraints = motorDiscOrBase
                         ? RigidbodyConstraints.FreezePositionX |
                               RigidbodyConstraints.FreezePositionY |
                               RigidbodyConstraints.FreezePositionZ |
                               RigidbodyConstraints.FreezeRotationX |
                               RigidbodyConstraints.FreezeRotationZ
                         : RigidbodyConstraints.FreezePositionY |
                               RigidbodyConstraints.FreezeRotationX |
                               RigidbodyConstraints.FreezeRotationZ;
  }

  private void CreateDrawingCanvas() {
    _hasLastInkPoint = false;
    if (!enableDrawing)
      return;
    _canvas = new GameObject("rotating square drawing canvas pivot");
    _canvas.transform.SetParent(transform, false);
    _canvas.transform.localPosition = new Vector3(0.0f, 0.10f, 0.15f);
    var paper = GameObject.CreatePrimitive(PrimitiveType.Cube);
    paper.name = "rotating square drawing canvas";
    paper.transform.SetParent(_canvas.transform, false);
    paper.transform.localPosition = Vector3.zero;
    paper.transform.localScale = new Vector3(canvasSize, 0.025f, canvasSize);
    paper.GetComponent<Renderer>().sharedMaterial = MakeMaterial(
        "Warm paper canvas", new Color(0.92f, 0.86f, 0.74f), 0.0f, 0.55f);
    ConfigureGeneratedCollider(paper);
    var inkObject = new GameObject("generated ink line");
    inkObject.transform.SetParent(_canvas.transform, false);
    inkObject.transform.localPosition = Vector3.up * 0.035f;
    _inkLine = inkObject.AddComponent<LineRenderer>();
    _inkLine.useWorldSpace = false;
    _inkLine.widthMultiplier = 0.008f;
    _inkLine.numCapVertices = 2;
    _inkLine.numCornerVertices = 2;
    _inkLine.material = MakeMaterial("Graphite ink", inkColor, 0.0f, 0.25f);
    _inkLine.startColor = inkColor;
    _inkLine.endColor = inkColor;
    _inkLine.positionCount = 0;
  }

  private void UpdateDrawingCanvas() {
    if (!enableDrawing || _canvas == null || _inkLine == null ||
        _markerTip == null || maxInkPoints <= 0)
      return;
    _canvas.transform.Rotate(Vector3.up, canvasRotationSpeed * Time.fixedDeltaTime,
                             Space.Self);
    Vector3 inkPoint = drawComplexSpirographPattern
                           ? GetComplexSpirographPoint(Time.fixedTime)
                           : GetMarkerTipCanvasPoint();
    float half = canvasSize * 0.5f;
    if (Mathf.Abs(inkPoint.x) > half || Mathf.Abs(inkPoint.z) > half)
      return;
    if (_hasLastInkPoint &&
        Vector3.Distance(_lastInkPoint, inkPoint) < minDrawPointDistance)
      return;
    int index = _inkLine.positionCount;
    if (index >= maxInkPoints) {
      ShiftInkLineLeft();
      index = _inkLine.positionCount - 1;
    } else {
      _inkLine.positionCount = index + 1;
    }
    _inkLine.SetPosition(index, inkPoint);
    _lastInkPoint = inkPoint;
    _hasLastInkPoint = true;
  }

  private Vector3 GetMarkerTipCanvasPoint() {
    Vector3 localTip = _canvas.transform.InverseTransformPoint(
        _markerTip.transform.position);
    Vector3 scaled = new Vector3(localTip.x * markerTraceScale, 0.035f,
                                 localTip.z * markerTraceScale);
    float safeHalf = canvasSize * 0.46f;
    scaled.x = Mathf.Clamp(scaled.x, -safeHalf, safeHalf);
    scaled.z = Mathf.Clamp(scaled.z, -safeHalf, safeHalf);
    return scaled;
  }

  private Vector3 GetComplexSpirographPoint(float time) {
    float t = time * Mathf.PI * 2.0f * complexPatternSpeed;
    float slow = t * 0.37f;
    float medium = t * 1.73f;
    float fast = t * 2.91f;
    float radius = complexPatternRadius +
                   Mathf.Sin(medium) * complexPatternSecondaryRadius;
    float x = Mathf.Cos(slow) * radius +
              Mathf.Sin(fast + 0.45f) * complexPatternSecondaryRadius * 0.72f +
              Mathf.Cos(t * 4.07f) * complexPatternSecondaryRadius * 0.24f;
    float z = Mathf.Sin(slow) * radius -
              Mathf.Cos(fast * 0.83f) * complexPatternSecondaryRadius * 0.72f +
              Mathf.Sin(t * 3.19f + 1.1f) * complexPatternSecondaryRadius * 0.26f;
    return new Vector3(x, 0.035f, z);
  }

  private void ShiftInkLineLeft() {
    for (int i = 1; i < _inkLine.positionCount; i++)
      _inkLine.SetPosition(i - 1, _inkLine.GetPosition(i));
  }

  private GameObject CreateMarkerHolder(Vector3 markerNode) {
    var pin = CreatePassivePin("Central marker hinge stack", markerNode, 0.25f);
    _markerHolder = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
    _markerHolder.name = "white vertical marker holder";
    _markerHolder.transform.SetParent(pin.transform, false);
    _markerHolder.transform.localPosition = new Vector3(0.09f, 0.0f, -0.04f);
    _markerHolder.transform.localScale = new Vector3(0.05f, 0.34f, 0.05f);
    _markerHolder.GetComponent<Renderer>().sharedMaterial = MarkerHolderMaterial;
    ConfigureGeneratedCollider(_markerHolder);
    _markerTip = CreateConePrimitive("marker drawing tip");
    _markerTip.transform.SetParent(pin.transform, false);
    _markerTip.transform.localPosition = new Vector3(0.09f, -0.31f, -0.04f);
    _markerTip.transform.localScale = new Vector3(0.04f, 0.12f, 0.04f);
    _markerTip.GetComponent<Renderer>().sharedMaterial = MarkerTipMaterial;
    ConfigureGeneratedCollider(_markerTip);
    return pin;
  }

  private static GameObject CreateConePrimitive(string name) {
    var cone = new GameObject(name);
    var meshFilter = cone.AddComponent<MeshFilter>();
    cone.AddComponent<MeshRenderer>();
    int sides = 32;
    var vertices = new Vector3[sides + 2];
    var triangles = new int[sides * 6];
    vertices[0] = Vector3.up * 0.5f;
    vertices[1] = Vector3.down * 0.5f;
    for (int i = 0; i < sides; i++) {
      float a = (Mathf.PI * 2.0f * i) / sides;
      vertices[i + 2] =
          new Vector3(Mathf.Cos(a) * 0.5f, -0.5f, Mathf.Sin(a) * 0.5f);
    }
    int t = 0;
    for (int i = 0; i < sides; i++) {
      int current = i + 2;
      int next = ((i + 1) % sides) + 2;
      triangles[t++] = 0;
      triangles[t++] = current;
      triangles[t++] = next;
      triangles[t++] = 1;
      triangles[t++] = next;
      triangles[t++] = current;
    }
    var mesh = new Mesh {
      name = name + " mesh",
      vertices = vertices,
      triangles = triangles
    };
    mesh.RecalculateNormals();
    meshFilter.sharedMesh = mesh;
    return cone;
  }

  private Material AluminiumMaterial { get; set; }
  private Material MotorMaterial { get; set; }
  private Material DiscTopMaterial { get; set; }
  private Material BoltMaterial { get; set; }
  private Material MarkerHolderMaterial { get; set; }
  private Material MarkerTipMaterial { get; set; }

  private void CreateMaterialsIfNeeded() {
    AluminiumMaterial = MakeMaterial("Brushed aluminium - satin silver",
        new Color(0.78f, 0.80f, 0.78f), 1.0f, 0.40f);
    MotorMaterial = MakeMaterial("Dark graphite stepper bodies",
        new Color(0.025f, 0.028f, 0.032f), 0.0f, 0.72f);
    DiscTopMaterial = MakeMaterial("Charcoal plywood-edged discs",
        new Color(0.045f, 0.038f, 0.030f), 0.05f, 0.55f);
    BoltMaterial = MakeMaterial("Warm brushed steel bolts",
                                new Color(0.78f, 0.70f, 0.56f), 1.0f, 0.28f);
    MarkerHolderMaterial = MakeMaterial("Clean white marker holder",
                                        new Color(0.95f, 0.96f, 0.93f), 0.0f,
                                        0.38f);
    MarkerTipMaterial = MakeMaterial("Soft graphite marker tip",
        new Color(0.035f, 0.033f, 0.030f), 0.0f, 0.42f);
  }

  private static Material MakeMaterial(string name, Color color, float metallic,
                                       float smoothness) {
    Shader shader = Shader.Find("Universal Render Pipeline/Unlit");
    if (shader == null)
      shader = Shader.Find("Unlit/Color");
    if (shader == null)
      shader = Shader.Find("Sprites/Default");
    if (shader == null)
      shader = Shader.Find("Standard");

    var material = new Material(shader) {
      name = name,
      color = color
    };
    if (material.HasProperty("_BaseColor"))
      material.SetColor("_BaseColor", color);
    if (material.HasProperty("_Color"))
      material.SetColor("_Color", color);
    if (material.HasProperty("_Metallic"))
      material.SetFloat("_Metallic", metallic);
    if (material.HasProperty("_Glossiness"))
      material.SetFloat("_Glossiness", smoothness);
    if (material.HasProperty("_Smoothness"))
      material.SetFloat("_Smoothness", smoothness);
    return material;
  }

  private void ClearChildren() {
    for (int i = transform.childCount - 1; i >= 0; i--) {
      var child = transform.GetChild(i).gameObject;
      if (Application.isPlaying)
        Destroy(child);
      else
        DestroyImmediate(child);
    }
  }

  private void OnDrawGizmos() {
    if (!debugMode)
      return;
    Gizmos.color = motorAxisColor;
    DrawAxis(leftMotorPosition);
    DrawAxis(centerMotorPosition);
    DrawAxis(rightMotorPosition);
    Gizmos.color = hingePointColor;
    foreach (var hinge in _freeHinges)
      if (hinge != null)
        Gizmos.DrawSphere(hinge.transform.TransformPoint(hinge.anchor), 0.045f);
    Gizmos.color = linkDebugColor;
    foreach (var link in _links)
      if (link.Body != null)
        Gizmos.DrawWireCube(link.Body.worldCenterOfMass, Vector3.one * 0.055f);
  }

  private void DrawAxis(Vector3 localPosition) {
    Vector3 p = transform.TransformPoint(localPosition + Vector3.up * 0.42f);
    Gizmos.DrawLine(p - Vector3.up * 0.35f, p + Vector3.up * 0.35f);
  }

  private void OnGUI() {
    if (!Application.isPlaying || !showRuntimeMotorUi)
      return;
    EnsureRuntimeUiStyles();
    GUILayout.BeginArea(new Rect(16, 16, 340, 286), _runtimePanelStyle);
    GUILayout.Label("Motor speed controls", _runtimeTitleStyle);
    GUILayout.Space(6.0f);
    playDemoOnStart = GUILayout.Toggle(playDemoOnStart, "Demo drive",
                                       _runtimeToggleStyle);
    GUILayout.Space(8.0f);
    DrawMotorSpeedControl("Left motor", ref demoLeftFrequency,
                          DefaultDemoLeftFrequency);
    DrawMotorSpeedControl("Center motor", ref demoCenterFrequency,
                          DefaultDemoCenterFrequency);
    DrawMotorSpeedControl("Right motor", ref demoRightFrequency,
                          DefaultDemoRightFrequency);
    GUILayout.Space(6.0f);
    if (GUILayout.Button("Reset all motor speeds", _runtimeButtonStyle,
                         GUILayout.Height(28.0f)))
      ResetAllMotorSpeeds();
    GUILayout.EndArea();
  }

  private void DrawMotorSpeedControl(string label, ref float frequency,
                                     float defaultFrequency) {
    float speed = FrequencyToSpeed(frequency);
    GUILayout.Label($"{label}: {speed:F0}°/s", _runtimeLabelStyle);
    speed = GUILayout.HorizontalSlider(speed, uiMinimumMotorSpeedDegPerSecond,
                                       uiMaximumMotorSpeedDegPerSecond,
                                       GUILayout.Height(22.0f));
    frequency = SpeedToFrequency(speed);
    if (GUILayout.Button($"Reset {label}", _runtimeButtonStyle,
                         GUILayout.Height(24.0f)))
      frequency = defaultFrequency;
    GUILayout.Space(6.0f);
  }


  private void EnsureRuntimeUiStyles() {
    if (_runtimeUiBackgroundTexture == null) {
      _runtimeUiBackgroundTexture = new Texture2D(1, 1) {
        name = "Runtime motor UI background"
      };
      _runtimeUiBackgroundTexture.SetPixel(0, 0, runtimeUiBackgroundColor);
      _runtimeUiBackgroundTexture.Apply();
    }
    _runtimePanelStyle = new GUIStyle(GUI.skin.box) {
      padding = new RectOffset(14, 14, 12, 12),
      margin = new RectOffset(0, 0, 0, 0)
    };
    _runtimePanelStyle.normal.background = _runtimeUiBackgroundTexture;
    _runtimePanelStyle.normal.textColor = runtimeUiTextColor;
    _runtimeTitleStyle = new GUIStyle(GUI.skin.label) {
      fontSize = 16,
      fontStyle = FontStyle.Bold,
      normal = { textColor = runtimeUiTextColor }
    };
    _runtimeLabelStyle = new GUIStyle(GUI.skin.label) {
      fontSize = 13,
      normal = { textColor = runtimeUiTextColor }
    };
    _runtimeToggleStyle = new GUIStyle(GUI.skin.toggle) {
      fontSize = 13,
      normal = { textColor = runtimeUiTextColor },
      onNormal = { textColor = runtimeUiTextColor }
    };
    _runtimeButtonStyle = new GUIStyle(GUI.skin.button) {
      fontSize = 13,
      fontStyle = FontStyle.Bold
    };
  }

  private void ApplyCameraBackground() {
    if (!forceWhiteCameraBackground)
      return;
    foreach (Camera camera in Camera.allCameras) {
      if (camera == null)
        continue;
      camera.clearFlags = CameraClearFlags.SolidColor;
      camera.backgroundColor = sceneBackgroundColor;
    }
  }

  private void ResetAllMotorSpeeds() {
    demoLeftFrequency = DefaultDemoLeftFrequency;
    demoCenterFrequency = DefaultDemoCenterFrequency;
    demoRightFrequency = DefaultDemoRightFrequency;
  }

  private static float FrequencyToSpeed(float frequency) => frequency * 360.0f;
  private static float SpeedToFrequency(float speedDegPerSecond) =>
      speedDegPerSecond / 360.0f;

  private readonly struct LayoutOverrides {
    public LayoutOverrides(Vector3? leftOuter, Vector3? topApex,
                           Vector3? rightOuter, Vector3? lowerLeftKnuckle,
                           Vector3? lowerRightKnuckle, Vector3? leftMotorVisual,
                           Vector3? centerMotorVisual,
                           Vector3? rightMotorVisual, Vector3? markerNode) {
      LeftOuter = leftOuter;
      TopApex = topApex;
      RightOuter = rightOuter;
      LowerLeftKnuckle = lowerLeftKnuckle;
      LowerRightKnuckle = lowerRightKnuckle;
      LeftMotorVisual = leftMotorVisual;
      CenterMotorVisual = centerMotorVisual;
      RightMotorVisual = rightMotorVisual;
      MarkerNode = markerNode;
    }

    public Vector3? LeftOuter { get; }
    public Vector3? TopApex { get; }
    public Vector3? RightOuter { get; }
    public Vector3? LowerLeftKnuckle { get; }
    public Vector3? LowerRightKnuckle { get; }
    public Vector3? LeftMotorVisual { get; }
    public Vector3? CenterMotorVisual { get; }
    public Vector3? RightMotorVisual { get; }
    public Vector3? MarkerNode { get; }
  }

  private readonly struct MotorVisualShell {
    public MotorVisualShell(Transform root, Transform disc, Transform pin) {
      Root = root;
      Disc = disc;
      Pin = pin;
    }

    public Transform Root { get; }
    public Transform Disc { get; }
    public Transform Pin { get; }
  }

  private readonly struct MotorVisualFollower {
    public MotorVisualFollower(Transform driveDisc, Transform drivePin,
                               Transform visualRoot, Transform visualDisc,
                               Transform visualPin, bool followPinPosition) {
      DriveDisc = driveDisc;
      DrivePin = drivePin;
      VisualRoot = visualRoot;
      VisualDisc = visualDisc;
      VisualPin = visualPin;
      FollowPinPosition = followPinPosition;
    }

    public Transform DriveDisc { get; }
    public Transform DrivePin { get; }
    public Transform VisualRoot { get; }
    public Transform VisualDisc { get; }
    public Transform VisualPin { get; }
    public bool FollowPinPosition { get; }
  }

  private sealed class MotorAssembly {
    public MotorAssembly(string name, GameObject root, GameObject disc,
                         Rigidbody discBody, HingeJoint axisJoint,
                         GameObject pinBody, Rigidbody pinRigidbody) {
      Name = name;
      Root = root;
      Disc = disc;
      DiscBody = discBody;
      AxisJoint = axisJoint;
      PinBody = pinBody;
      PinRigidbody = pinRigidbody;
    }

    public string Name { get; }
    public GameObject Root { get; }
    public GameObject Disc { get; }
    public Rigidbody DiscBody { get; }
    public HingeJoint AxisJoint { get; }
    public GameObject PinBody { get; }
    public Rigidbody PinRigidbody { get; }
    public float DemoAngle { get; set; }
    public Vector3 PinWorldPosition => PinBody.transform.position;
  }

  private readonly struct LinkInfo {
    public LinkInfo(string name, float length, Rigidbody body) {
      Name = name;
      Length = length;
      Body = body;
    }

    public string Name { get; }
    public float Length { get; }
    public Rigidbody Body { get; }
  }
}
}
