# API Reference[](#api-reference)

## Module-Level API[](#module-level-api)

Top-level functions available directly on the ` litlogger ` module.

### Initialization[](#initialization)

### init[](#init)

`litlogger.init.init(name=None, root_dir=None, teamspace=None, metadata=None, store_step=True, store_created_at=False, save_logs=False, print_url=True, verbose=True, * *kwargs)`

Initialize a litlogger experiment for standalone usage.

Example:

`1 2 3 4 5 6 7 8 ` ` import litlogger litlogger.init(name="my-experiment") for i in range(100): litlogger.log({"loss": 1.0 / (i + 1), "accuracy": i / 100.0}, step=i) litlogger.finalize()`

* *Parameters: **

  - * *name ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Name of your experiment \(defaults to a generated name\).

  - * *root\_dir ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Folder where logs and metadata are stored \(default: ./lightning\_logs\).

  - * *teamspace ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | Teamspace | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Teamspace where charts and artifacts will appear.

  - * *metadata ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [str](https://docs.python.org/3/library/stdtypes.html#str) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Extra metadata to associate with the experiment as tags.

  - * *store\_step ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Whether to store the step field with each logged value.

  - * *store\_created\_at ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Whether to store a creation timestamp with each value.

  - * *save\_logs ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – If True, capture and upload terminal logs.

  - * *print\_url ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print the experiment URL and initialization info.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – If True, print styled console output. Defaults to True.

  - * *\ *\ *kwargs ** \( ` [Any](https://docs.python.org/3/library/typing.html#typing.Any) ` \) – Additional keyword arguments. Will be forwarded to the Experiment constructor.

  - * *name ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *root\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *teamspace ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` Teamspace` ` |` ` None ` \)

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] ` ` | ` ` None ` \)

  - * *store\_step ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) ` |` ` None ` \)

  - * *store\_created\_at ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) ` |` ` None ` \)

  - * *save\_logs ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *print\_url ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *kwargs ** \( [ ` Any ` ](https://docs.python.org/3/library/typing.html#typing.Any) \)


* *Returns: ** The initialized experiment instance.

* *Return type: ** Experiment

### finish[](#finish)

`litlogger.init.finish(status=None)`

Finalize the current experiment.

This is an alias for litlogger.finalize\(\).

* *Parameters: **

  - * *status ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional status string to mark the experiment with.

  - * *status ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Return type: ** None

### get\_metadata[](#getmetadata)

`litlogger.init.get_metadata()`

Get the metadata associated with the current experiment.

* *Returns: ** The metadata dictionary with key-value pairs from the metrics stream.

* *Return type: ** dict\[str, str\]

* *Raises: **

  - [ ` RuntimeError ` ](https://docs.python.org/3/library/exceptions.html#RuntimeError) – If litlogger.init\(\) has not been called.


### Logging Functions[](#logging-functions)

These functions are available as module-level callables after ` litlogger.init() ` is called. They delegate to the underlying [ ` Experiment ` ](#litlogger.experiment.Experiment) instance.

### log[](#log)

`litlogger.log(self, metrics=None, step=None, * *kwargs)`

Log metrics to the experiment with background uploading.

Metrics are buffered locally and uploaded to the cloud in batches to optimize performance. The batch is sent when either 1 second has passed or 1000 values have been logged.

* *Parameters: **

  - * *metrics ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [float](https://docs.python.org/3/library/functions.html#float) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Dictionary mapping metric names to numeric values. Example: \{“loss”: 0.5, “accuracy”: 0.95\}.

  - * *step ** \( ` [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional step number for this data point \(e.g., training step, epoch\). If None and store\_step=True, no step is recorded.

  - * *kwargs ** \( ` [float](https://docs.python.org/3/library/functions.html#float) ` \) – Additional metric values. Can be used to provide metrics more natural. Example: loss=0.5, accuracy: 0.95.

  - * *metrics ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` float ` ](https://docs.python.org/3/library/functions.html#float) ` ] ` ` | ` ` None ` \)

  - * *step ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) ` |` ` None ` \)

  - * *kwargs ** \( [ ` Any ` ](https://docs.python.org/3/library/typing.html#typing.Any) \)


* *Raises: **

  - [ ` RuntimeError ` ](https://docs.python.org/3/library/exceptions.html#RuntimeError) – If the background thread encountered an error.


* *Return type: ** None

### log\_metrics[](#logmetrics)

`litlogger.log_metrics(self, metrics=None, step=None, * *kwargs)`

Log metrics to the experiment with background uploading.

Metrics are buffered locally and uploaded to the cloud in batches to optimize performance. The batch is sent when either 1 second has passed or 1000 values have been logged.

* *Parameters: **

  - * *metrics ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [float](https://docs.python.org/3/library/functions.html#float) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Dictionary mapping metric names to numeric values. Example: \{“loss”: 0.5, “accuracy”: 0.95\}.

  - * *step ** \( ` [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional step number for this data point \(e.g., training step, epoch\). If None and store\_step=True, no step is recorded.

  - * *kwargs ** \( ` [float](https://docs.python.org/3/library/functions.html#float) ` \) – Additional metric values. Can be used to provide metrics more natural. Example: loss=0.5, accuracy: 0.95.

  - * *metrics ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` float ` ](https://docs.python.org/3/library/functions.html#float) ` ] ` ` | ` ` None ` \)

  - * *step ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) ` |` ` None ` \)

  - * *kwargs ** \( [ ` Any ` ](https://docs.python.org/3/library/typing.html#typing.Any) \)


* *Raises: **

  - [ ` RuntimeError ` ](https://docs.python.org/3/library/exceptions.html#RuntimeError) – If the background thread encountered an error.


* *Return type: ** None

### log\_metadata[](#logmetadata)

`litlogger.log_metadata(self, metadata=None, * *kwargs)`

Add or update metadata tags on the experiment.

Merges the provided key-value pairs into the experiment’s existing metadata and pushes the update to the cloud immediately.

* *Parameters: **

  - * *metadata ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [str](https://docs.python.org/3/library/stdtypes.html#str) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Dictionary of metadata key-value pairs to add or update. Example: \{“optimizer”: “adam”, “lr”: “0.001”\}.

  - * *\ *\ *kwargs ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Additional metadata as keyword arguments. Example: optimizer=”adam”, lr=”0.001”.

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] ` ` | ` ` None ` \)

  - * *kwargs ** \( [ ` Any ` ](https://docs.python.org/3/library/typing.html#typing.Any) \)


* *Return type: ** None

### log\_file[](#logfile)

`litlogger.log_file(self, path, remote_path=None, verbose=True)`

Upload a file artifact to the cloud for this experiment.

The file is uploaded to cloud storage and registered with the experiment, making it visible in the artifacts view and accessible via get\_file\(\).

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path to the local file to upload. Can be absolute or relative.

  - * *remote\_path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Path relative to experiment root for storage and display. If None, uses the path relative to cwd if under cwd, otherwise basename. Example: remote\_path=”images/0.png” will store and display as “images/0.png”.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print a confirmation message after upload. Defaults to True.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *remote\_path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Return type: ** None

### get\_file[](#getfile)

`litlogger.get_file(self, path, remote_path=None, verbose=True)`

Download a file artifact from the cloud for this experiment.

The file is downloaded from cloud storage \(previously uploaded via log\_file\) and saved to the specified local path.

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path where the file should be saved locally. Parent directories are created if needed.

  - * *remote\_path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Path relative to experiment root where the file is stored. If None, uses the path relative to cwd if under cwd, otherwise basename. Must match the remote\_path used during log\_file\(\) for correct resolution.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print a confirmation message after download. Defaults to True.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *remote\_path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Returns: ** The local path where the file was saved \(same as the input path\).

* *Return type: ** str

### log\_model[](#logmodel)

`litlogger.log_model(self, model, staging_dir=None, verbose=False, version=None, metadata=None)`

Save and upload a model object to cloud storage using litmodels.

This saves a live model object \(e.g., PyTorch module, LightningModule\) to disk using framework-specific serialization, then uploads it to the litmodels registry.

For uploading pre-saved model files, use log\_model\_artifact\(\) instead.

* *Parameters: **

  - * *model ** \( ` [Any](https://docs.python.org/3/library/typing.html#typing.Any) ` \) – The model object to save and upload \(e.g., torch.nn.Module, LightningModule\).

  - * *staging\_dir ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional local directory for staging the model before upload. If None, uses a temp directory.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar during upload. Defaults to False.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *metadata ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional metadata dictionary to store with the model \(e.g., hyperparameters, metrics\).

  - * *model ** \( [ ` Any ` ](https://docs.python.org/3/library/typing.html#typing.Any) \)

  - * *staging\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` |` ` None ` \)


* *Returns: ** Information about the uploaded model \(details from litmodels\).

* *Return type: ** str

### get\_model[](#getmodel)

`litlogger.get_model(self, staging_dir=None, verbose=False, version=None)`

Get a model object using litmodels load\_model.

* *Parameters: **

  - * *staging\_dir ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional directory where the model will be downloaded.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *staging\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Return type: ** Any

* *Returns: ** The loaded model object.

### log\_model\_artifact[](#logmodelartifact)

`litlogger.log_model_artifact(self, path, verbose=False, version=None)`

Upload a model file or directory to cloud storage using litmodels.

This uploads raw model files \(e.g., weights.pt, checkpoint.ckpt\) or entire directories to the litmodels registry. Use this when you have pre-saved model files.

For saving model objects directly, use log\_model\(\) instead.

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path to the local model file or directory to upload.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar during upload. Defaults to False.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Return type: ** None

### get\_model\_artifact[](#getmodelartifact)

`litlogger.get_model_artifact(self, path, verbose=False, version=None)`

Download a model artifact file or directory from cloud storage using litmodels.

This downloads raw model files or directories that were previously uploaded via log\_model\_artifact\(\). The files are saved to the specified local path.

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path where the model should be saved locally. Directories are created if needed.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar during download. Defaults to False.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Returns: ** The local path where the model was saved \(same as the input path\).

* *Return type: ** str

### finalize[](#finalize)

`litlogger.finalize(self, status=None, print_summary=True)`

Finalize the experiment and upload all remaining metrics.

This method waits for the background thread to finish uploading all queued metrics, and uploads terminal logs if save\_logs=True. It’s automatically called on exit via an atexit handler, but can also be called manually.

This method is idempotent and can be called multiple times safely.

* *Parameters: **

  - * *status ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional status string for the experiment \(currently unused, reserved for future use\).

  - * *print\_summary ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print the run completion summary. Defaults to True.

  - * *status ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *print\_summary ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Return type: ** None

## Experiment[](#experiment)

### class Experiment[](#class-experiment)

`class litlogger.experiment.Experiment(name, log_dir='lightning_logs', save_logs=False, teamspace=None, light_color=None, dark_color=None, metadata=None, store_step=True, store_created_at=False, max_batch_size=1000, rate_limiting_interval=1, verbose=True)`

Bases: [ ` object ` ](https://docs.python.org/3/library/functions.html#object)

High-level interface to log, store, and fetch metrics and artifacts of all kinds.

This class manages the full lifecycle of an experiment on Lightning.ai, including: - Creating a metrics stream with automatic buffering and batching - Uploading metrics to the cloud in the background - Logging and retrieving files, models, and model artifacts - Gracefully finalizing the experiment on exit \(via atexit handler\)

The experiment can be used directly or via the module-level API \(litlogger.init\(\)\).

Initialize an experiment for logging to the <https://lightning.ai> platform.

* *Parameters: **

  - * *name ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – A human-friendly name for your experiment.

  - * *log\_dir ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Local directory where temporary logs/artifacts are stored. Defaults to “lightning\_logs”.

  - * *save\_logs ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – If True, capture and upload terminal output as a file artifact. Defaults to False.

  - * *teamspace ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | Teamspace | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Teamspace in which to create and display the charts. If None, uses your default teamspace.

  - * *light\_color ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Hex color of the curve in light mode \(overrides the random default\). Example: “\#FF5733”.

  - * *dark\_color ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Hex color of the curve in dark mode \(overrides the random default\). Example: “\#3498DB”.

  - * *metadata ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [str](https://docs.python.org/3/library/stdtypes.html#str) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Key-value parameters associated with the experiment \(displayed as tags in the UI\).

  - * *store\_step ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Whether to store the provided step for each data point. Defaults to True.

  - * *store\_created\_at ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Whether to store a creation timestamp for each data point. Defaults to False.

  - * *max\_batch\_size ** \( ` [int](https://docs.python.org/3/library/functions.html#int) ` \) – Number of metric values to batch before uploading. Defaults to 1000.

  - * *rate\_limiting\_interval ** \( ` [int](https://docs.python.org/3/library/functions.html#int) ` \) – Minimum seconds between uploads. Defaults to 1.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – If True, print styled console output. Defaults to True.

  - * *name ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *log\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *save\_logs ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *teamspace ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` Teamspace` ` |` ` None ` \)

  - * *light\_color ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *dark\_color ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] ` ` | ` ` None ` \)

  - * *store\_step ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) ` |` ` None ` \)

  - * *store\_created\_at ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) ` |` ` None ` \)

  - * *max\_batch\_size ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) \)

  - * *rate\_limiting\_interval ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


# finalize[](#finalize)

`finalize(status=None, print_summary=True)`

Finalize the experiment and upload all remaining metrics.

This method waits for the background thread to finish uploading all queued metrics, and uploads terminal logs if save\_logs=True. It’s automatically called on exit via an atexit handler, but can also be called manually.

This method is idempotent and can be called multiple times safely.

* *Parameters: **

  - * *status ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional status string for the experiment \(currently unused, reserved for future use\).

  - * *print\_summary ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print the run completion summary. Defaults to True.

  - * *status ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *print\_summary ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Return type: ** None

# get\_file[](#getfile)

`get_file(path, remote_path=None, verbose=True)`

Download a file artifact from the cloud for this experiment.

The file is downloaded from cloud storage \(previously uploaded via log\_file\) and saved to the specified local path.

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path where the file should be saved locally. Parent directories are created if needed.

  - * *remote\_path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Path relative to experiment root where the file is stored. If None, uses the path relative to cwd if under cwd, otherwise basename. Must match the remote\_path used during log\_file\(\) for correct resolution.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print a confirmation message after download. Defaults to True.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *remote\_path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Returns: ** The local path where the file was saved \(same as the input path\).

* *Return type: ** str

# get\_model[](#getmodel)

`get_model(staging_dir=None, verbose=False, version=None)`

Get a model object using litmodels load\_model.

* *Parameters: **

  - * *staging\_dir ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional directory where the model will be downloaded.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *staging\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Return type: ** Any

* *Returns: ** The loaded model object.

# get\_model\_artifact[](#getmodelartifact)

`get_model_artifact(path, verbose=False, version=None)`

Download a model artifact file or directory from cloud storage using litmodels.

This downloads raw model files or directories that were previously uploaded via log\_model\_artifact\(\). The files are saved to the specified local path.

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path where the model should be saved locally. Directories are created if needed.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar during download. Defaults to False.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Returns: ** The local path where the model was saved \(same as the input path\).

* *Return type: ** str

# log\_file[](#logfile)

`log_file(path, remote_path=None, verbose=True)`

Upload a file artifact to the cloud for this experiment.

The file is uploaded to cloud storage and registered with the experiment, making it visible in the artifacts view and accessible via get\_file\(\).

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path to the local file to upload. Can be absolute or relative.

  - * *remote\_path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Path relative to experiment root for storage and display. If None, uses the path relative to cwd if under cwd, otherwise basename. Example: remote\_path=”images/0.png” will store and display as “images/0.png”.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print a confirmation message after upload. Defaults to True.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *remote\_path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Return type: ** None

# log\_files[](#logfiles)

`log_files(paths, remote_paths=None, max_workers=10)`

Upload multiple file artifacts to the cloud in parallel.

This is more efficient than calling log\_file\(\) multiple times when you have many files, as it handles them in parallel.

* *Parameters: **

  - * *paths ** \( ` [list](https://docs.python.org/3/library/stdtypes.html#list) [ [str](https://docs.python.org/3/library/stdtypes.html#str) ] ` \) – List of paths to local files to upload.

  - * *remote\_paths ** \( ` [list](https://docs.python.org/3/library/stdtypes.html#list) [ [str](https://docs.python.org/3/library/stdtypes.html#str) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional list of remote paths, one for each file in paths. If provided, must have same length as paths. If None, each file uses its default remote path \(relative to cwd or basename\).

  - * *max\_workers ** \( ` [int](https://docs.python.org/3/library/functions.html#int) ` \) – Maximum number of concurrent uploads. Defaults to 10.

  - * *paths ** \( [ ` list ` ](https://docs.python.org/3/library/stdtypes.html#list) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] `\)

  - * *remote\_paths ** \( [ ` list ` ](https://docs.python.org/3/library/stdtypes.html#list) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] ` ` | ` ` None ` \)

  - * *max\_workers ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) \)


* *Return type: ** None

# log\_media[](#logmedia)

`log_media(name, path, kind=None, step=None, epoch=None, caption=None, verbose=False)`

Upload a media file \(image, text, etc.\) to the experiment.

* *Parameters: **

  - * *name ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Name of the media.

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Local path to the media file.

  - * *kind ** \( ` MediaType | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Type of media \(MediaType.IMAGE or MediaType.TEXT\). If None, attempts to guess from file extension or mime type.

  - * *step ** \( ` [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional training step.

  - * *epoch ** \( ` [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional training epoch.

  - * *caption ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional caption for the media.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to print a confirmation message after upload.

  - * *name ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *kind ** \( ` MediaType` ` |` ` None ` \)

  - * *step ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) ` |` ` None ` \)

  - * *epoch ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) ` |` ` None ` \)

  - * *caption ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)


* *Raises: **

  - [ ` ValueError ` ](https://docs.python.org/3/library/exceptions.html#ValueError) – If the file type cannot be determined or is not supported.

  - [ ` FileNotFoundError ` ](https://docs.python.org/3/library/exceptions.html#FileNotFoundError) – If the file does not exist.


* *Return type: ** None

# log\_metadata[](#logmetadata)

`log_metadata(metadata=None, * *kwargs)`

Add or update metadata tags on the experiment.

Merges the provided key-value pairs into the experiment’s existing metadata and pushes the update to the cloud immediately.

* *Parameters: **

  - * *metadata ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [str](https://docs.python.org/3/library/stdtypes.html#str) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Dictionary of metadata key-value pairs to add or update. Example: \{“optimizer”: “adam”, “lr”: “0.001”\}.

  - * *\ *\ *kwargs ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Additional metadata as keyword arguments. Example: optimizer=”adam”, lr=”0.001”.

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] ` ` | ` ` None ` \)

  - * *kwargs ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)


* *Return type: ** None

# log\_metrics[](#logmetrics)

`log_metrics(metrics=None, step=None, * *kwargs)`

Log metrics to the experiment with background uploading.

Metrics are buffered locally and uploaded to the cloud in batches to optimize performance. The batch is sent when either 1 second has passed or 1000 values have been logged.

* *Parameters: **

  - * *metrics ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [float](https://docs.python.org/3/library/functions.html#float) ] | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Dictionary mapping metric names to numeric values. Example: \{“loss”: 0.5, “accuracy”: 0.95\}.

  - * *step ** \( ` [int](https://docs.python.org/3/library/functions.html#int) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional step number for this data point \(e.g., training step, epoch\). If None and store\_step=True, no step is recorded.

  - * *kwargs ** \( ` [float](https://docs.python.org/3/library/functions.html#float) ` \) – Additional metric values. Can be used to provide metrics more natural. Example: loss=0.5, accuracy: 0.95.

  - * *metrics ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` float ` ](https://docs.python.org/3/library/functions.html#float) ` ] ` ` | ` ` None ` \)

  - * *step ** \( [ ` int ` ](https://docs.python.org/3/library/functions.html#int) ` |` ` None ` \)

  - * *kwargs ** \( [ ` float ` ](https://docs.python.org/3/library/functions.html#float) \)


* *Raises: **

  - [ ` RuntimeError ` ](https://docs.python.org/3/library/exceptions.html#RuntimeError) – If the background thread encountered an error.


* *Return type: ** None

# log\_metrics\_batch[](#logmetricsbatch)

`log_metrics_batch(metrics)`

Log a batch of metrics through the background queue.

This method converts the batch format to Metrics objects and pushes them through the background queue, which handles batching and chunking to respect API limits.

Example:

`1 2 3 4 5 6 7 8 9 10 ` ` { "loss": [ {"step": 0, "value": 1.0}, {"step": 1, "value": 0.5}, ], "accuracy": [ {"step": 0, "value": 0.6}, {"step": 1, "value": 0.8}, ], }`

* *Raises: **

  - [ ` RuntimeError ` ](https://docs.python.org/3/library/exceptions.html#RuntimeError) – If the background thread encountered an error.


* *Parameters: **

  - * *metrics ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [list](https://docs.python.org/3/library/stdtypes.html#list) [ [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [float](https://docs.python.org/3/library/functions.html#float) ]]] ` \) – Dictionary mapping metric names to lists of dicts with “step” and “value” keys.

  - * *metrics ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` list ` ](https://docs.python.org/3/library/stdtypes.html#list) ` [ ` [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` float ` ](https://docs.python.org/3/library/functions.html#float) ` ]` ` ]` ` ] `\)


* *Return type: ** None

* *Parameters: **

  - * *metrics ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` list ` ](https://docs.python.org/3/library/stdtypes.html#list) ` [ ` [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` float ` ](https://docs.python.org/3/library/functions.html#float) ` ]` ` ]` ` ] `\)


* *Return type: ** None

# log\_model[](#logmodel)

`log_model(model, staging_dir=None, verbose=False, version=None, metadata=None)`

Save and upload a model object to cloud storage using litmodels.

This saves a live model object \(e.g., PyTorch module, LightningModule\) to disk using framework-specific serialization, then uploads it to the litmodels registry.

For uploading pre-saved model files, use log\_model\_artifact\(\) instead.

* *Parameters: **

  - * *model ** \( ` [Any](https://docs.python.org/3/library/typing.html#typing.Any) ` \) – The model object to save and upload \(e.g., torch.nn.Module, LightningModule\).

  - * *staging\_dir ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional local directory for staging the model before upload. If None, uses a temp directory.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar during upload. Defaults to False.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *metadata ** \( ` [dict](https://docs.python.org/3/library/stdtypes.html#dict) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional metadata dictionary to store with the model \(e.g., hyperparameters, metrics\).

  - * *model ** \( [ ` Any ` ](https://docs.python.org/3/library/typing.html#typing.Any) \)

  - * *staging\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` |` ` None ` \)


* *Returns: ** Information about the uploaded model \(details from litmodels\).

* *Return type: ** str

# log\_model\_artifact[](#logmodelartifact)

`log_model_artifact(path, verbose=False, version=None)`

Upload a model file or directory to cloud storage using litmodels.

This uploads raw model files \(e.g., weights.pt, checkpoint.ckpt\) or entire directories to the litmodels registry. Use this when you have pre-saved model files.

For saving model objects directly, use log\_model\(\) instead.

* *Parameters: **

  - * *path ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) ` \) – Path to the local model file or directory to upload.

  - * *verbose ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – Whether to show progress bar during upload. Defaults to False.

  - * *version ** \( ` [str](https://docs.python.org/3/library/stdtypes.html#str) | [None](https://docs.python.org/3/library/constants.html#None) ` \) – Optional version string for the model.

  - * *path ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) \)

  - * *verbose ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *version ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


* *Return type: ** None

# print\_url[](#printurl)

`print_url()`

Print the experiment URL and initialization info with styled output.

* *Return type: ** None

# property metadata[](#property-metadata)

`property metadata: [dict](https://docs.python.org/3/library/stdtypes.html#dict) [[str](https://docs.python.org/3/library/stdtypes.html#str) , [str](https://docs.python.org/3/library/stdtypes.html#str) ]`

Get the metadata associated with this experiment from the metrics stream.

* *Returns: ** The metadata dictionary with key-value pairs from code-defined tags.

* *Return type: ** dict\[str, str\]

# property teamspace[](#property-teamspace)

`property teamspace: Teamspace`

Get the teamspace for this experiment.

* *Returns: ** The teamspace object.

* *Return type: ** Teamspace

# property url[](#property-url)

`property url: [str](https://docs.python.org/3/library/stdtypes.html#str) `

Get the direct URL to view this experiment in the Lightning.ai web interface.

* *Returns: ** The full URL to the experiment’s visualization page.

* *Return type: ** str

## Types[](#types)

### class MediaType[](#class-mediatype)

`class litlogger.types.MediaType( *values)`

Bases: [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) , [ ` Enum ` ](https://docs.python.org/3/library/enum.html#enum.Enum)

Type of media to upload.

Add row above

Add row below

Delete row

Add column to left

Add column to right

Delete column

Name

Value

IMAGE

'image'

TEXT

'text'

## LightningLogger[](#lightninglogger)

### class LightningLogger[](#class-lightninglogger)

`class litlogger.logger.LightningLogger(root_dir=None, name=None, teamspace=None, metadata=None, store_step=True, log_model=False, save_logs=True, checkpoint_name=None)`

Bases: [ ` LitLogger ` ](https://lightning.ai/docs/pytorch/stable/api/lightning.pytorch.loggers.litlogger.html#lightning.pytorch.loggers.litlogger.LitLogger)

Initialize the LightningLogger.

Example:

`1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 ` ` from lightning.pytorch import Trainer from lightning.pytorch.demos.boring_classes import BoringModel, BoringDataModule from lightning.pytorch.loggers.litlogger import LitLogger class LoggingModel(BoringModel): def training_step(self, batch, batch_idx: int): loss = self.step(batch) # logging the computed loss self.log("train_loss", loss) return {"loss": loss} trainer = Trainer( max_epochs=10, enable_model_summary=False, logger=LitLogger("./lightning_logs", name="boring_model") ) model = BoringModel() data_module = BoringDataModule() trainer.fit(model, data_module) trainer.test(model, data_module)`

* *Parameters: **

  - * *root\_dir ** \( ` Union [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [Path](https://docs.python.org/3/library/pathlib.html#pathlib.Path) , [None](https://docs.python.org/3/library/constants.html#None) ] ` \) – Folder where logs and metadata are stored \(default: ./lightning\_logs\).

  - * *name ** \( ` [Optional](https://docs.python.org/3/library/typing.html#typing.Optional) [ [str](https://docs.python.org/3/library/stdtypes.html#str) ] ` \) – Name of your experiment \(defaults to a generated name\).

  - * *teamspace ** \( ` [Optional](https://docs.python.org/3/library/typing.html#typing.Optional) [ [str](https://docs.python.org/3/library/stdtypes.html#str) ] ` \) – Teamspace name where charts and artifacts will appear.

  - * *metadata ** \( ` [Optional](https://docs.python.org/3/library/typing.html#typing.Optional) [ [dict](https://docs.python.org/3/library/stdtypes.html#dict) [ [str](https://docs.python.org/3/library/stdtypes.html#str) , [str](https://docs.python.org/3/library/stdtypes.html#str) ]] ` \) – Extra metadata to associate with the experiment as tags.

  - * *log\_model ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – If True, automatically log model checkpoints as artifacts.

  - * *save\_logs ** \( ` [bool](https://docs.python.org/3/library/functions.html#bool) ` \) – If True, capture and upload terminal logs.

  - * *checkpoint\_name ** \( ` [Optional](https://docs.python.org/3/library/typing.html#typing.Optional) [ [str](https://docs.python.org/3/library/stdtypes.html#str) ] ` \) – Override the base name for logged checkpoints.

  - * *root\_dir ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` | ` [ ` Path ` ](https://docs.python.org/3/library/pathlib.html#pathlib.Path) ` |` ` None ` \)

  - * *name ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *teamspace ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)

  - * *metadata ** \( [ ` dict ` ](https://docs.python.org/3/library/stdtypes.html#dict) ` [ ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` , ` [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` ] ` ` | ` ` None ` \)

  - * *store\_step ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *log\_model ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *save\_logs ** \( [ ` bool ` ](https://docs.python.org/3/library/functions.html#bool) \)

  - * *checkpoint\_name ** \( [ ` str ` ](https://docs.python.org/3/library/stdtypes.html#str) ` |` ` None ` \)


