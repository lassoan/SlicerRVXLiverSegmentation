import qt
import slicer

from .RVesselXUtils import createInputNodeSelector, addInCollapsibleLayout, WidgetUtils, createButton
from .VerticalLayoutWidget import VerticalLayoutWidget


class DataWidget(VerticalLayoutWidget):
  """
  Object responsible for loading and showing the input volume to the user.
  Provides buttons to load DICOM and other data.
  Enables listeners to be notified when the input volume has been changed by the user.
  """

  def __init__(self):
    """
    Configure DataTab with load DICOM and Load Data buttons, Input volume selection, Volume 2D and 3D rendering
    """

    VerticalLayoutWidget.__init__(self, "Data Tab")

    # Create input layout
    inputLayout = qt.QHBoxLayout()
    inputLabel = qt.QLabel("Volume: ")
    inputLayout.addWidget(inputLabel)

    # Create input volume selector and connect callback to selection changed signal
    self._volumeDisplayNode = None
    self._sceneObserver = None
    self.inputSelector = createInputNodeSelector("vtkMRMLScalarVolumeNode", toolTip="Pick the input.",
                                                 callBack=self.onInputSelectorNodeChanged)

    # Add load DICOM and load DATA button to the layout
    inputLayout.addWidget(self.inputSelector)
    inputLayout.addWidget(createButton("Load DICOM", self.onLoadDICOMClicked))
    inputLayout.addWidget(createButton("Load Data", self.onLoadDataClicked))
    self._verticalLayout.addLayout(inputLayout)

    # Add Volume information
    volumesWidget = slicer.util.getNewModuleGui(slicer.modules.volumes)
    addInCollapsibleLayout(volumesWidget, self._verticalLayout, "Volume")

    # Hide Volumes Selector and its label
    WidgetUtils.hideChildrenContainingName(volumesWidget, "activeVolume")
    self.volumesModuleSelector = WidgetUtils.getFirstChildContainingName(volumesWidget, "ActiveVolumeNodeSelector")

    # Add Volume Rendering information
    volumeRenderingWidget = slicer.util.getNewModuleGui(slicer.modules.volumerendering)
    addInCollapsibleLayout(volumeRenderingWidget, self._verticalLayout, "Volume Rendering")

    # Hide Volume Rendering Selector and its label
    self.volumeRenderingModuleVisibility = WidgetUtils.hideFirstChildContainingName(volumeRenderingWidget,
                                                                                    "VisibilityCheckBox")
    self.volumeRenderingModuleSelector = WidgetUtils.hideFirstChildContainingName(volumeRenderingWidget,
                                                                                  "VolumeNodeComboBox")

    # Add stretch
    self._verticalLayout.addStretch(1)

    # Connect volume changed callback
    self._inputNodeChangedCallbacks = [self.setVolumeNode]

  def addInputNodeChangedCallback(self, callback):
    """Adds new callback to list of callbacks triggered when data tab input node is changed. When the node is changed to
    a valid value, the callback will be called.

    Parameters
    ----------
    callback: Callable[[vtkMRMLNode], None] function to call with new input node when changed
    """
    self._inputNodeChangedCallbacks.append(callback)

  def onInputSelectorNodeChanged(self, node):
    """On input changed and with a valid input node, notifies all callbacks of new node value

    Parameters
    ----------
    node: vtkMRMLNode
    """
    # Early return if invalid node
    if not node:
      return

    self._removePreviousNodeAddedObserverFromScene()

    # If node not yet properly initialized, attach observer to image change.
    # Else notify image changed and save node as new input volume
    if node.GetImageData() is None:
      self._attachNodeAddedObserverToScene(node)
    else:
      self._notifyInputChanged(node)

  def _removePreviousNodeAddedObserverFromScene(self):
    slicer.mrmlScene.RemoveObserver(self._sceneObserver)

  def _attachNodeAddedObserverToScene(self, node):
    self._sceneObserver = slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent,
                                                       lambda *x: self.onInputSelectorNodeChanged(node))

  def _notifyInputChanged(self, node):
    for callback in self._inputNodeChangedCallbacks:
      callback(node)

  def onLoadDICOMClicked(self):
    """Show DICOM Widget as popup
    """
    try:
      dicomWidget = slicer.modules.DICOMWidget
    except:
      dicomWidget = slicer.modules.dicom.widgetRepresentation().self()

    if dicomWidget is not None:
      dicomWidget.detailsPopup.open()

  def onLoadDataClicked(self):
    slicer.app.ioManager().openAddDataDialog()

  def setVolumeNode(self, node):
    """
    Set input selector and volume rendering nodes as input node.
    Show the new input node in 3D rendering.

    Parameters
    ----------
    node: vtkMRMLVolumeNode
    """
    # Change node in input selector and volume rendering widgets
    self.inputSelector.setCurrentNode(node)

    if self.volumesModuleSelector:
      self.volumesModuleSelector.setCurrentNode(node)

    if self.volumeRenderingModuleSelector:
      self.volumeRenderingModuleSelector.setCurrentNode(node)

    # Show node in 2D view
    slicer.util.setSliceViewerLayers(node)

    # Show node in 3D view
    self.showVolumeRendering(node)

  def showVolumeRendering(self, volumeNode):
    """Show input volumeNode in 3D View

    Parameters
    ----------
    volumeNode: vtkMRMLVolumeNode
    """
    # Early return if invalid volume node
    if volumeNode is None:
      return

    volRenLogic = slicer.modules.volumerendering.logic()

    # hide previous node if necessary
    if self._volumeDisplayNode:
      self._volumeDisplayNode.SetVisibility(False)

    # Create new display node for input volume
    self._volumeDisplayNode = volRenLogic.CreateDefaultVolumeRenderingNodes(volumeNode)
    self._volumeDisplayNode.SetVisibility(True)
    slicer.util.resetThreeDViews()

    # Load preset
    # https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Show_volume_rendering_automatically_when_a_volume_is_loaded
    scalarRange = volumeNode.GetImageData().GetScalarRange()
    if scalarRange[1] - scalarRange[0] < 1500:
      # small dynamic range, probably MRI
      self._volumeDisplayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName('MR-Default'))
    else:
      # larger dynamic range, probably CT
      self._volumeDisplayNode.GetVolumePropertyNode().Copy(volRenLogic.GetPresetByName('CT-Chest-Contrast-Enhanced'))

  def getInputNode(self):
    """
    Returns
    -------
    vtkMRMLVolumeNode
      Current vtkMRMLVolumeNode selected by user in the DataWidget
    """
    return self.inputSelector.currentNode()