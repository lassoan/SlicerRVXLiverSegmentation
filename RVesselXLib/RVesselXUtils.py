import logging
import os

import ctk
import qt
import slicer


class Icons(object):
  """ Object responsible for the different icons in the module. The module doesn't have any icons internally but pulls
  icons from slicer and the other modules.
  """

  toggleVisibility = qt.QIcon(":/Icons/VisibleOrInvisible.png")
  visibleOn = qt.QIcon(":/Icons/VisibleOn.png")
  visibleOff = qt.QIcon(":/Icons/VisibleOff.png")
  editSegmentation = qt.QIcon(":/Icons/Paint.png")
  editPoint = qt.QIcon(":/Icons/Paint.png")
  delete = qt.QIcon(":/Icons/SnapshotDelete.png")
  cut3d = qt.QIcon(":/Icons/Medium/SlicerEditCut.png")


class WidgetUtils(object):
  """Helper class to extract widgets linked to an existing widget representation
  """

  @staticmethod
  def getChildrenContainingName(widget, childString):
    if not hasattr(widget, "children"):
      return []
    else:
      return [child for child in widget.children() if childString.lower() in child.name.lower()]

  @staticmethod
  def getFirstChildContainingName(widget, childString):
    children = WidgetUtils.getChildrenContainingName(widget, childString)
    return children[0] if children else None

  @staticmethod
  def getChildrenOfType(widget, childType):
    if not hasattr(widget, "children"):
      return []
    else:
      return [child for child in widget.children() if isinstance(child, childType)]

  @staticmethod
  def getFirstChildOfType(widget, childType):
    children = WidgetUtils.getChildrenOfType(widget, childType)
    return children[0] if children else None

  @staticmethod
  def hideChildrenContainingName(widget, childString):
    hiddenChildren = WidgetUtils.getChildrenContainingName(widget, childString)
    for child in WidgetUtils.getChildrenContainingName(widget, childString):
      child.visible = False
    return hiddenChildren

  @staticmethod
  def hideFirstChildContainingName(widget, childString):
    hiddenChild = WidgetUtils.getFirstChildContainingName(widget, childString)
    if hiddenChild:
      hiddenChild.visible = False
    return hiddenChild


class Settings(object):
  """Helper class to get and set settings in Slicer with RVesselX tag
  """

  @staticmethod
  def _withPrefix(key):
    return "RVesselX/" + key

  @staticmethod
  def value(key, defaultValue=None):
    return slicer.app.settings().value(Settings._withPrefix(key), defaultValue)

  @staticmethod
  def setValue(key, value):
    slicer.app.settings().setValue(Settings._withPrefix(key), value)

  @staticmethod
  def _exportDirectoryKey():
    return "ExportDirectory"

  @staticmethod
  def exportDirectory():
    return Settings.value(Settings._exportDirectoryKey(), "")

  @staticmethod
  def setExportDirectory(value):
    Settings.setValue(Settings._exportDirectoryKey(), value)


class GeometryExporter(object):
  """Helper object to export mrml types to given output directory
  """

  def __init__(self, **elementsToExport):
    """Class can be instantiated with dictionary of elements to export. Key represents the export name of the element and
    value the slicer MRML Node to export

    Parameters
    ----------
    elementsToExport: keyword args of elements to export
    """
    self._elementsToExport = elementsToExport

  def exportToDirectory(self, selectedDir):
    """Export all stored elements to selected directory.

    Parameters
    ----------
    selectedDir: str. Path to export directory
    """
    for elementName, elementNode in self._elementsToExport.items():
      # Select format depending on node type
      formatExtension = self._elementExportExtension(elementNode)

      if formatExtension is not None:
        outputPath = os.path.join(selectedDir, elementName + formatExtension)
        exportSuccessful = slicer.util.saveNode(elementNode, outputPath)
        if not exportSuccessful:
          logging.warn("Failed to export file : %s at location %s" % (elementName, outputPath))

  @staticmethod
  def _elementExportExtension(elementNode):
    """Extracts export extension for input node given its class. Volumes will be exported as NIFTI files, Models as VTK
    files. Other nodes are not supported and function will return None.

    Parameters
    ----------
    elementNode: slicer.vtkMRMLNode type
    Returns
    -------
      str or None
    """
    if isinstance(elementNode, slicer.vtkMRMLVolumeNode):  # Export volumes as NIFTI files
      return ".nii"
    elif isinstance(elementNode, slicer.vtkMRMLModelNode):  # Export meshes as vtk types
      return ".vtk"
    else:  # Other types are not supported for export
      return None

  def __setitem__(self, key, value):
    self._elementsToExport[key] = value

  def __getitem__(self, key):
    return self._elementsToExport[key]

  def keys(self):
    return self._elementsToExport.keys()


def jumpSlicesToLocation(location):
  """Helper function to position all the different slices to input location.

  Parameters
  ----------
  location: List[float] with x, y, z components
  """
  slicer.modules.markups.logic().JumpSlicesToLocation(location[0], location[1], location[2], True)


def jumpSlicesToNthMarkupPosition(markupNode, i_nthMarkup):
  """Helper function to position all the different slices to the nth markup position in input node

  Parameters
  ----------
  markupNode: vtkMRMLMarkupsFiducialNode
    Fiducial node with at least i_nthMarkup + 1 nodes
  i_nthMarkup: int or None
    Index of the markup we want to center the slices on
  """
  # Early return if incorrect markupNode or index
  if not isinstance(markupNode, slicer.vtkMRMLMarkupsFiducialNode):
    return

  isMarkupIndexInRange = 0 <= i_nthMarkup < markupNode.GetNumberOfFiducials()
  if i_nthMarkup is None or not isMarkupIndexInRange:
    return

  # Get fiducial position and center slices to it
  pos = [0] * 3
  markupNode.GetNthFiducialPosition(i_nthMarkup, pos)
  jumpSlicesToLocation(pos)


def createInputNodeSelector(nodeType, toolTip, callBack=None):
  """Creates node selector with given input node type, tooltip and callback when currentNodeChanged signal is emitted

  Parameters
  ----------
  nodeType: vtkMRML type compatible with qMRMLNodeComboBox
    Node type which will be displayed in the combo box
  toolTip: str
    Input selector hover text
  callBack: (optional) function
    Function called when qMRMLNodeComboBox currentNodeChanged is triggered.
    Function must accept a vtkMRMLNode input parameter

  Returns
  -------
  inputSelector : qMRMLNodeComboBox
    configured input selector
  """
  inputSelector = slicer.qMRMLNodeComboBox()
  inputSelector.nodeTypes = [nodeType]
  inputSelector.selectNodeUponCreation = False
  inputSelector.addEnabled = False
  inputSelector.removeEnabled = False
  inputSelector.noneEnabled = False
  inputSelector.showHidden = False
  inputSelector.showChildNodeTypes = False
  inputSelector.setMRMLScene(slicer.mrmlScene)
  inputSelector.setToolTip(toolTip)
  if callBack is not None:
    inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", callBack)
  return inputSelector


def createSingleMarkupFiducial(toolTip, markupName, markupColor=qt.QColor("red")):
  """Creates node selector for vtkMarkupFiducial type containing only one point.

  Parameters
  ----------
  toolTip: str
    Input selector hover text
  markupName: str
    Default name for the created markups when new markup is selected
  markupColor: (option) QColor
    Default color for the newly created markups (default = red)

  Returns
  -------
  qSlicerSimpleMarkupsWidget
  """
  markupNodeSelector = slicer.qSlicerSimpleMarkupsWidget()
  markupNodeSelector.objectName = markupName + 'NodeSelector'
  markupNodeSelector.toolTip = toolTip
  markupNodeSelector.setNodeBaseName(markupName)
  markupNodeSelector.tableWidget().hide()
  markupNodeSelector.defaultNodeColor = markupColor
  markupNodeSelector.markupsSelectorComboBox().noneEnabled = False
  markupNodeSelector.markupsPlaceWidget().placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceSingleMarkup
  markupNodeSelector.setMRMLScene(slicer.mrmlScene)
  slicer.app.connect('mrmlSceneChanged(vtkMRMLScene*)', markupNodeSelector, 'setMRMLScene(vtkMRMLScene*)')
  return markupNodeSelector


def createMultipleMarkupFiducial(toolTip, markupName, markupColor=qt.QColor("red")):
  """Creates node selector for vtkMarkupFiducial type containing only multiple points.

  Parameters
  ----------
  toolTip: str
    Input selector hover text
  markupName: str
    Default name for the created markups when new markup is selected
  markupColor: (option) QColor
    Default color for the newly created markups (default = red)

  Returns
  -------
  qSlicerSimpleMarkupsWidget
  """
  markupNodeSelector = createSingleMarkupFiducial(toolTip=toolTip, markupName=markupName, markupColor=markupColor)
  markupNodeSelector.markupsPlaceWidget().placeMultipleMarkups = slicer.qSlicerMarkupsPlaceWidget.ForcePlaceMultipleMarkups
  markupNodeSelector.markupsPlaceWidget().setPlaceModePersistency(True)
  return markupNodeSelector


def createButton(name, callback=None, isCheckable=False):
  """Helper function to create a button with a text, callback on click and checkable status

  Parameters
  ----------
  name: str
    Label of the button
  callback: Callable
    Called method when button is clicked
  isCheckable: bool
    If true, the button will be checkable

  Returns
  -------
  QPushButton
  """
  button = qt.QPushButton(name)
  if callback is not None:
    button.connect("clicked(bool)", callback)
  button.setCheckable(isCheckable)
  return button


def createFiducialNode(name, *positions):
  """Creates a vtkMRMLMarkupsFiducialNode with one point at given position and with given name

  Parameters
  ----------
  positions : list of list of positions
    size 3 position list with positions for created fiducial point
  name : str
    Base for unique name given to the output node

  Returns
  -------
  vtkMRMLMarkupsFiducialNode with one point at given position
  """
  fiducialPoint = slicer.mrmlScene.CreateNodeByClass("vtkMRMLMarkupsFiducialNode")
  fiducialPoint.UnRegister(None)
  fiducialPoint.SetName(slicer.mrmlScene.GetUniqueNameByString(name))
  for position in positions:
    fiducialPoint.AddFiducialFromArray(position)
  return slicer.mrmlScene.AddNode(fiducialPoint)


def createLabelMapVolumeNodeBasedOnModel(modelVolume, volumeName):
  """Creates new LabelMapVolume node which reproduces the input node orientation, spacing, and origins

  Parameters
  ----------
  modelVolume : vtkMRMLLabelMapVolumeNode
    Volume from which orientation, spacing and origin will be deduced
  volumeName: str
    base name for the volume when it will be added to slicer scene. A unique name will be derived
    from this base name (ie : adding number indices in case the volume is already present in the scene)

  Returns
  -------
  vtkMRMLLabelMapVolumeNode
    New Label map volume added to the scene
  """
  newLabelMapNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLLabelMapVolumeNode")
  newLabelMapNode.UnRegister(None)
  newLabelMapNode.CopyOrientation(modelVolume)
  newLabelMapNode.SetName(slicer.mrmlScene.GetUniqueNameByString(volumeName))
  return addToScene(newLabelMapNode)


def createModelNode(modelName):
  """Creates new Model node with given input volume Name

  Parameters
  ----------
  modelName: str
    base name for the model when it will be added to slicer scene. A unique name will be derived
    from this base name (ie : adding number indices in case the model is already present in the scene)

  Returns
  -------
  vtkMRMLModelNode
    New model added to the scene
  """
  newModelNode = slicer.mrmlScene.CreateNodeByClass("vtkMRMLModelNode")
  newModelNode.UnRegister(None)
  newModelNode.SetName(slicer.mrmlScene.GetUniqueNameByString(modelName))
  return addToScene(newModelNode)


def addInCollapsibleLayout(childWidget, parentLayout, collapsibleText, isCollapsed=True):
  """Wraps input childWidget into a collapsible button attached to input parentLayout.
  collapsibleText is writen next to collapsible button. Initial collapsed status is customizable
  (collapsed by default)
  """
  collapsibleButton = ctk.ctkCollapsibleButton()
  collapsibleButton.text = collapsibleText
  collapsibleButton.collapsed = isCollapsed
  parentLayout.addWidget(collapsibleButton)
  collapsibleButtonLayout = qt.QVBoxLayout()
  collapsibleButtonLayout.addWidget(childWidget)
  collapsibleButton.setLayout(collapsibleButtonLayout)


def removeNoneList(elements):
  """
  Parameters
  ----------
  elements: object or List[object]

  Returns
  -------
  List[object] with no None values
  """
  if not isinstance(elements, list):
    elements = [elements]
  return [elt for elt in elements if elt is not None]


def removeFromMRMLScene(nodesToRemove):
  """Removes the input nodes from the scene. Nodes will no longer be accessible from the mrmlScene or from the UI.

  Parameters
  ----------
  nodesToRemove: List[vtkMRMLNode] or vtkMRMLNode
    Objects to remove from the scene
  """
  nodesInScene = [node for node in removeNoneList(nodesToRemove) if slicer.mrmlScene.IsNodePresent(node)]
  for node in nodesInScene:
    slicer.mrmlScene.RemoveNode(node)


def getMarkupIdPositionDictionary(markup):
  """
  Parameters
  ----------
  markup : vtkMRMLMarkupsFiducialNode

  Returns
  -------
  Dict[str, List[float]]
    Dictionary containing the node ids contained in the markup node and its associated positions
  """
  markupDict = {}
  for i in range(markup.GetNumberOfFiducials()):
    nodeId = markup.GetNthFiducialLabel(i)
    nodePosition = [0] * 3
    markup.GetNthFiducialPosition(i, nodePosition)
    markupDict[nodeId] = nodePosition
  return markupDict


def getFiducialPositions(fiducialNode):
  """ Extracts positions from input fiducial node and returns it as array of positions

  Parameters
  ----------
  fiducialNode : vtkMRMLMarkupsFiducialNode
    FiducialNode from which we want the coordinates

  Returns
  -------
  List of arrays[3] of fiducial positions
  """
  positions = []
  for i in range(fiducialNode.GetNumberOfFiducials()):
    pos = [0, 0, 0]
    fiducialNode.GetNthFiducialPosition(i, pos)
    positions.append(pos)
  return positions


def hideFromUser(modelsToHide, hideFromEditor=True):
  """Hides the input models from the user and from the editor if option is set.

  Parameters
  ----------
  modelsToHide: List[vtkMRMLNode] or vtkMRMLNode
    Objects to hide from the user
  hideFromEditor: (option) bool
    If set to true, will hide the nodes from both views and the editor. Else they will be only hidden from views.
    default = True
  """
  for model in removeNoneList(modelsToHide):
    model.SetDisplayVisibility(False)
    if hideFromEditor:
      model.SetHideFromEditors(True)


def addToScene(node):
  """Add input node to scene and return node

  Parameters
  ----------
  node: vtkMRMLNode
    Node to add to scene

  Returns
  -------
  node after having added it to scene
  """
  outputNode = slicer.mrmlScene.AddNode(node)
  outputNode.CreateDefaultDisplayNodes()
  return outputNode


def raiseValueErrorIfInvalidType(**kwargs):
  """Verify input type satisfies the expected type and raise in case it doesn't.

  Expected input dictionary : "valueName":(value, "expectedType").
  If value is None or value is not an instance of expectedType, method will raise ValueError with text indicating
  valueName, value and expected type
  """

  for valueName, values in kwargs.items():
    # Get value and expect type from dictionary
    value, expType = values

    # Get type from slicer in case of string input
    if isinstance(expType, str):
      expType = getattr(slicer, expType)

    # Verify value is of correct instance
    if not isinstance(value, expType):
      raise ValueError("%s Type error.\nExpected : %s but got %s." % (valueName, expType, type(value)))