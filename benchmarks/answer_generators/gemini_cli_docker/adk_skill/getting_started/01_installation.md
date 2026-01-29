
# Installation

## Python

### Stable Release (Recommended)

You can install the latest stable version of ADK using `pip`:

```bash
pip install google-adk
```

The release cadence is weekly.

This version is recommended for most users as it represents the most recent official release.

### Development Version
Bug fixes and new features are merged into the main branch on GitHub first. If you need access to changes that haven't been included in an official PyPI release yet, you can install directly from the main branch:

```bash
pip install git+https://github.com/google/adk-python.git@main
```

Note: The development version is built directly from the latest code commits. While it includes the newest fixes and features, it may also contain experimental changes or bugs not present in the stable release. Use it primarily for testing upcoming changes or accessing critical fixes before they are officially released.

## Java

You can either use maven or gradle to add the `google-adk` and `google-adk-dev` package.

`google-adk` is the core Java ADK library. Java ADK also comes with a pluggable example SpringBoot server to run your agents seamlessly. This optional
package is present as part of `google-adk-dev`.

If you are using maven, add the following to your `pom.xml`:

```xml
<dependencies>
  <!-- The ADK Core dependency -->
  <dependency>
    <groupId>com.google.adk</groupId>
    <artifactId>google-adk</artifactId>
    <version>0.1.0</version>
  </dependency>
  
  <!-- The ADK Dev Web UI to debug your agent (Optional) -->
  <dependency>
    <groupId>com.google.adk</groupId>
    <artifactId>google-adk-dev</artifactId>
    <version>0.1.0</version>
  </dependency>
</dependencies>
```

If you are using gradle, add the dependency to your build.gradle:

```
dependencies {
    implementation 'com.google.adk:google-adk:0.1.0'
    implementation 'com.google.adk:google-adk-dev:0.1.0'
}
```
