## How to use sitespeed budgets

See [documentation](https://www.sitespeed.io/documentation/continuous-integration) on using sitespeed budgets in a CI system.

In addition, some noteworthy details are documented here.

#### Notes
* If a particular rule is set to 0, it will instead use the default setting
* Whatever bar you set on the budget for an item, sitespeed must find a better score.

To take an example, see this json configuration:


```
{
  "rules": {
  	"default": 77,
	"criticalpath": -1,
	"cssnumreq": 79,
	"jsnumreq": 0,
  }
}
```

In this example,

* If `criticalpath` is found as 0 or better, the test will pass.
* `cssnumreq` will fail if the score is 79, and it will pass for 80 or better.
* `jsnumreq`, despite your best intentions, will actually assert on 77, not 0.
* `longexpirehead`, which is not listed, will assert on a 77 (i.e., the default)
