# Onshape CAD Parser

Parses Onshape documents into sketch / extrude / revolve command sequences (JSON), with B-spline sketch curves converted to cubic Bézier segments.

> [!WARNING]
> The use of this library without prior permission from Onshape/PTC constitutes a violation of the [Terms of Use](https://www.onshape.com/en/legal/terms-of-use). Specifically,
>
> *You shall not and shall not allow a third party to: [...] Use any robot, spider, scraper or other automated means to access the Service, or use any data mining, data gathering or extraction method;*
>
> Please contact Onshape Support before using a library such as this to access documents in bulk via the Onshape API.

## Setup

Requires Python 2.7 (for the Onshape API client).

```sh
git clone --recursive https://github.com/Yijie-Ding/O-CDT.git
cd O-CDT/parser

conda create -n onshape_parser python=2.7
conda activate onshape_parser
pip install -r requirements.txt
```

Copy `creds.example.json` to `creds.json` and fill in your Onshape API keys.

## Usage

```sh
python process.py --test                                    # test example -> examples/
python process.py --link_data_folder /path/to/abc/links     # ABC Onshape links -> processed/
```
