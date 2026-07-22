/*
 *  Copyright (c) 2026-present, Nexthop Systems, Inc.
 *  All rights reserved.
 *
 *  This source code is licensed under the BSD-style license found in the
 *  LICENSE file in the root directory of this source tree. An additional grant
 *  of patent rights can be found in the PATENTS file in the same directory.
 *
 */

#include "fboss/agent/platforms/common/nh5010f/Nh5010fPlatformMapping.h"

namespace {
constexpr auto kJsonPlatformMappingStr = R"(
{
  "ports": {
    "1": {
        "mapping": {
          "id": 1,
          "name": "eth1/1/1",
          "controllingPort": 5,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 1,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                2,
                3,
                4,
                5,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                2,
                3,
                4,
                5,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                2,
                3,
                4,
                5,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                2,
                3,
                4,
                5,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                5
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "2": {
        "mapping": {
          "id": 2,
          "name": "eth1/1/2",
          "controllingPort": 6,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 2,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                6
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "3": {
        "mapping": {
          "id": 3,
          "name": "eth1/1/3",
          "controllingPort": 7,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 3,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                7
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "4": {
        "mapping": {
          "id": 4,
          "name": "eth1/1/4",
          "controllingPort": 8,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 4,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip1",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "5": {
        "mapping": {
          "id": 5,
          "name": "eth1/2/1",
          "controllingPort": 1,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 5,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                1,
                2,
                3,
                4,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                1,
                2,
                3,
                4,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                1,
                2,
                3,
                4,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                1,
                2,
                3,
                4,
                6,
                7,
                8
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                1
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "6": {
        "mapping": {
          "id": 6,
          "name": "eth1/2/2",
          "controllingPort": 5,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 6,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                2
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "7": {
        "mapping": {
          "id": 7,
          "name": "eth1/2/3",
          "controllingPort": 5,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 7,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                3
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "8": {
        "mapping": {
          "id": 8,
          "name": "eth1/2/4",
          "controllingPort": 5,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 8,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                4
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core8",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip2",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "9": {
        "mapping": {
          "id": 9,
          "name": "eth1/3/1",
          "controllingPort": 13,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 9,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                10,
                11,
                12,
                13,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                10,
                11,
                12,
                13,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                10,
                11,
                12,
                13,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                10,
                11,
                12,
                13,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                13
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "10": {
        "mapping": {
          "id": 10,
          "name": "eth1/3/2",
          "controllingPort": 14,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 10,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                14
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "11": {
        "mapping": {
          "id": 11,
          "name": "eth1/3/3",
          "controllingPort": 15,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 11,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                15
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "12": {
        "mapping": {
          "id": 12,
          "name": "eth1/3/4",
          "controllingPort": 16,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 12,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip3",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "13": {
        "mapping": {
          "id": 13,
          "name": "eth1/4/1",
          "controllingPort": 9,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 13,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                9,
                10,
                11,
                12,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                9,
                10,
                11,
                12,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                9,
                10,
                11,
                12,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                9,
                10,
                11,
                12,
                14,
                15,
                16
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                9
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "14": {
        "mapping": {
          "id": 14,
          "name": "eth1/4/2",
          "controllingPort": 13,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 14,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                10
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "15": {
        "mapping": {
          "id": 15,
          "name": "eth1/4/3",
          "controllingPort": 13,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 15,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                11
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "16": {
        "mapping": {
          "id": 16,
          "name": "eth1/4/4",
          "controllingPort": 13,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 16,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                12
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core9",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip4",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "17": {
        "mapping": {
          "id": 17,
          "name": "eth1/5/1",
          "controllingPort": 21,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 17,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                18,
                19,
                20,
                21,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                18,
                19,
                20,
                21,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                18,
                19,
                20,
                21,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                18,
                19,
                20,
                21,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                21
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "18": {
        "mapping": {
          "id": 18,
          "name": "eth1/5/2",
          "controllingPort": 22,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 18,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                22
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "19": {
        "mapping": {
          "id": 19,
          "name": "eth1/5/3",
          "controllingPort": 23,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 19,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                23
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "20": {
        "mapping": {
          "id": 20,
          "name": "eth1/5/4",
          "controllingPort": 24,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 20,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip5",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "21": {
        "mapping": {
          "id": 21,
          "name": "eth1/6/1",
          "controllingPort": 17,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 21,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                17,
                18,
                19,
                20,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                17,
                18,
                19,
                20,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                17,
                18,
                19,
                20,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                17,
                18,
                19,
                20,
                22,
                23,
                24
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                17
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "22": {
        "mapping": {
          "id": 22,
          "name": "eth1/6/2",
          "controllingPort": 21,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 22,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                18
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "23": {
        "mapping": {
          "id": 23,
          "name": "eth1/6/3",
          "controllingPort": 21,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 23,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                19
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "24": {
        "mapping": {
          "id": 24,
          "name": "eth1/6/4",
          "controllingPort": 21,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 24,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                20
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core10",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip6",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "25": {
        "mapping": {
          "id": 25,
          "name": "eth1/7/1",
          "controllingPort": 29,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 25,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                26,
                27,
                28,
                29,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                26,
                27,
                28,
                29,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                26,
                27,
                28,
                29,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                26,
                27,
                28,
                29,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                29
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "26": {
        "mapping": {
          "id": 26,
          "name": "eth1/7/2",
          "controllingPort": 30,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 26,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                30
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "27": {
        "mapping": {
          "id": 27,
          "name": "eth1/7/3",
          "controllingPort": 31,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 27,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                31
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "28": {
        "mapping": {
          "id": 28,
          "name": "eth1/7/4",
          "controllingPort": 32,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 28,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip7",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "29": {
        "mapping": {
          "id": 29,
          "name": "eth1/8/1",
          "controllingPort": 25,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 29,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                25,
                26,
                27,
                28,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                25,
                26,
                27,
                28,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                25,
                26,
                27,
                28,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                25,
                26,
                27,
                28,
                30,
                31,
                32
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                25
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "30": {
        "mapping": {
          "id": 30,
          "name": "eth1/8/2",
          "controllingPort": 29,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 30,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                26
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "31": {
        "mapping": {
          "id": 31,
          "name": "eth1/8/3",
          "controllingPort": 29,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 31,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                27
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "32": {
        "mapping": {
          "id": 32,
          "name": "eth1/8/4",
          "controllingPort": 29,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 2,
          "attachedCorePortIndex": 32,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                28
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core11",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip8",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "33": {
        "mapping": {
          "id": 33,
          "name": "eth1/9/1",
          "controllingPort": 37,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 25,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                34,
                35,
                36,
                37,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                34,
                35,
                36,
                37,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                34,
                35,
                36,
                37,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                34,
                35,
                36,
                37,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                37
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "34": {
        "mapping": {
          "id": 34,
          "name": "eth1/9/2",
          "controllingPort": 38,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 26,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                38
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "35": {
        "mapping": {
          "id": 35,
          "name": "eth1/9/3",
          "controllingPort": 39,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 27,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                39
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "36": {
        "mapping": {
          "id": 36,
          "name": "eth1/9/4",
          "controllingPort": 40,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 28,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip9",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "37": {
        "mapping": {
          "id": 37,
          "name": "eth1/10/1",
          "controllingPort": 33,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 29,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                33,
                34,
                35,
                36,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                33,
                34,
                35,
                36,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                33,
                34,
                35,
                36,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                33,
                34,
                35,
                36,
                38,
                39,
                40
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                33
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "38": {
        "mapping": {
          "id": 38,
          "name": "eth1/10/2",
          "controllingPort": 37,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 30,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                34
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "39": {
        "mapping": {
          "id": 39,
          "name": "eth1/10/3",
          "controllingPort": 37,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 31,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                35
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "40": {
        "mapping": {
          "id": 40,
          "name": "eth1/10/4",
          "controllingPort": 37,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 32,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                36
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core3",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip10",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "41": {
        "mapping": {
          "id": 41,
          "name": "eth1/11/1",
          "controllingPort": 45,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 17,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                42,
                43,
                44,
                45,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                42,
                43,
                44,
                45,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                42,
                43,
                44,
                45,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                42,
                43,
                44,
                45,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                45
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "42": {
        "mapping": {
          "id": 42,
          "name": "eth1/11/2",
          "controllingPort": 46,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 18,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                46
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "43": {
        "mapping": {
          "id": 43,
          "name": "eth1/11/3",
          "controllingPort": 47,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 19,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                47
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "44": {
        "mapping": {
          "id": 44,
          "name": "eth1/11/4",
          "controllingPort": 48,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 20,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip11",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "45": {
        "mapping": {
          "id": 45,
          "name": "eth1/12/1",
          "controllingPort": 41,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 21,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                41,
                42,
                43,
                44,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                41,
                42,
                43,
                44,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                41,
                42,
                43,
                44,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                41,
                42,
                43,
                44,
                46,
                47,
                48
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                41
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "46": {
        "mapping": {
          "id": 46,
          "name": "eth1/12/2",
          "controllingPort": 45,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 22,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                42
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "47": {
        "mapping": {
          "id": 47,
          "name": "eth1/12/3",
          "controllingPort": 45,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 23,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                43
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "48": {
        "mapping": {
          "id": 48,
          "name": "eth1/12/4",
          "controllingPort": 45,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 24,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                44
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core2",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip12",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "49": {
        "mapping": {
          "id": 49,
          "name": "eth1/13/1",
          "controllingPort": 53,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 9,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                50,
                51,
                52,
                53,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                50,
                51,
                52,
                53,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                50,
                51,
                52,
                53,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                50,
                51,
                52,
                53,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                53
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "50": {
        "mapping": {
          "id": 50,
          "name": "eth1/13/2",
          "controllingPort": 54,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 10,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                54
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "51": {
        "mapping": {
          "id": 51,
          "name": "eth1/13/3",
          "controllingPort": 55,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 11,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                55
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "52": {
        "mapping": {
          "id": 52,
          "name": "eth1/13/4",
          "controllingPort": 56,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 12,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip13",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "53": {
        "mapping": {
          "id": 53,
          "name": "eth1/14/1",
          "controllingPort": 49,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 13,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                49,
                50,
                51,
                52,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                49,
                50,
                51,
                52,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                49,
                50,
                51,
                52,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                49,
                50,
                51,
                52,
                54,
                55,
                56
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                49
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "54": {
        "mapping": {
          "id": 54,
          "name": "eth1/14/2",
          "controllingPort": 53,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 14,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                50
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "55": {
        "mapping": {
          "id": 55,
          "name": "eth1/14/3",
          "controllingPort": 53,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 15,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                51
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "56": {
        "mapping": {
          "id": 56,
          "name": "eth1/14/4",
          "controllingPort": 53,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 16,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                52
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core1",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip14",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "57": {
        "mapping": {
          "id": 57,
          "name": "eth1/15/1",
          "controllingPort": 61,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 1,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                58,
                59,
                60,
                61,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                58,
                59,
                60,
                61,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                58,
                59,
                60,
                61,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                58,
                59,
                60,
                61,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                61
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "58": {
        "mapping": {
          "id": 58,
          "name": "eth1/15/2",
          "controllingPort": 62,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 2,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                62
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "59": {
        "mapping": {
          "id": 59,
          "name": "eth1/15/3",
          "controllingPort": 63,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 3,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                63
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "60": {
        "mapping": {
          "id": 60,
          "name": "eth1/15/4",
          "controllingPort": 64,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 4,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip15",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "61": {
        "mapping": {
          "id": 61,
          "name": "eth1/16/1",
          "controllingPort": 57,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 5,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                57,
                58,
                59,
                60,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                57,
                58,
                59,
                60,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                57,
                58,
                59,
                60,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                57,
                58,
                59,
                60,
                62,
                63,
                64
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                57
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "62": {
        "mapping": {
          "id": 62,
          "name": "eth1/16/2",
          "controllingPort": 61,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 6,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                58
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "63": {
        "mapping": {
          "id": 63,
          "name": "eth1/16/3",
          "controllingPort": 61,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 7,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                59
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "64": {
        "mapping": {
          "id": 64,
          "name": "eth1/16/4",
          "controllingPort": 61,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 0,
          "attachedCorePortIndex": 8,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                60
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core0",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip16",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "65": {
        "mapping": {
          "id": 65,
          "name": "eth1/17/1",
          "controllingPort": 69,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 1,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                66,
                67,
                68,
                69,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                66,
                67,
                68,
                69,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                66,
                67,
                68,
                69,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                66,
                67,
                68,
                69,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                69
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "66": {
        "mapping": {
          "id": 66,
          "name": "eth1/17/2",
          "controllingPort": 70,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 2,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                70
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "67": {
        "mapping": {
          "id": 67,
          "name": "eth1/17/3",
          "controllingPort": 71,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 3,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                71
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "68": {
        "mapping": {
          "id": 68,
          "name": "eth1/17/4",
          "controllingPort": 72,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 4,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip17",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "69": {
        "mapping": {
          "id": 69,
          "name": "eth1/18/1",
          "controllingPort": 65,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 5,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                65,
                66,
                67,
                68,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                65,
                66,
                67,
                68,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                65,
                66,
                67,
                68,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                65,
                66,
                67,
                68,
                70,
                71,
                72
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                65
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "70": {
        "mapping": {
          "id": 70,
          "name": "eth1/18/2",
          "controllingPort": 69,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 6,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                66
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "71": {
        "mapping": {
          "id": 71,
          "name": "eth1/18/3",
          "controllingPort": 69,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 7,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                67
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "72": {
        "mapping": {
          "id": 72,
          "name": "eth1/18/4",
          "controllingPort": 69,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 8,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                68
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core20",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip18",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "73": {
        "mapping": {
          "id": 73,
          "name": "eth1/19/1",
          "controllingPort": 77,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 9,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                74,
                75,
                76,
                77,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                74,
                75,
                76,
                77,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                74,
                75,
                76,
                77,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                74,
                75,
                76,
                77,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                77
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "74": {
        "mapping": {
          "id": 74,
          "name": "eth1/19/2",
          "controllingPort": 78,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 10,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                78
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "75": {
        "mapping": {
          "id": 75,
          "name": "eth1/19/3",
          "controllingPort": 79,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 11,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                79
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "76": {
        "mapping": {
          "id": 76,
          "name": "eth1/19/4",
          "controllingPort": 80,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 12,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip19",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "77": {
        "mapping": {
          "id": 77,
          "name": "eth1/20/1",
          "controllingPort": 73,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 13,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                73,
                74,
                75,
                76,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                73,
                74,
                75,
                76,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                73,
                74,
                75,
                76,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                73,
                74,
                75,
                76,
                78,
                79,
                80
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                73
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "78": {
        "mapping": {
          "id": 78,
          "name": "eth1/20/2",
          "controllingPort": 77,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 14,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                74
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "79": {
        "mapping": {
          "id": 79,
          "name": "eth1/20/3",
          "controllingPort": 77,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 15,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                75
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "80": {
        "mapping": {
          "id": 80,
          "name": "eth1/20/4",
          "controllingPort": 77,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 16,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                76
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core21",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip20",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "81": {
        "mapping": {
          "id": 81,
          "name": "eth1/21/1",
          "controllingPort": 85,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 17,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                82,
                83,
                84,
                85,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                82,
                83,
                84,
                85,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                82,
                83,
                84,
                85,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                82,
                83,
                84,
                85,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                85
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "82": {
        "mapping": {
          "id": 82,
          "name": "eth1/21/2",
          "controllingPort": 86,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 18,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                86
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "83": {
        "mapping": {
          "id": 83,
          "name": "eth1/21/3",
          "controllingPort": 87,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 19,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                87
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "84": {
        "mapping": {
          "id": 84,
          "name": "eth1/21/4",
          "controllingPort": 88,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 20,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip21",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "85": {
        "mapping": {
          "id": 85,
          "name": "eth1/22/1",
          "controllingPort": 81,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 21,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                81,
                82,
                83,
                84,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                81,
                82,
                83,
                84,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                81,
                82,
                83,
                84,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                81,
                82,
                83,
                84,
                86,
                87,
                88
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                81
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "86": {
        "mapping": {
          "id": 86,
          "name": "eth1/22/2",
          "controllingPort": 85,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 22,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                82
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "87": {
        "mapping": {
          "id": 87,
          "name": "eth1/22/3",
          "controllingPort": 85,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 23,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                83
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "88": {
        "mapping": {
          "id": 88,
          "name": "eth1/22/4",
          "controllingPort": 85,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 24,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                84
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core22",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip22",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "89": {
        "mapping": {
          "id": 89,
          "name": "eth1/23/1",
          "controllingPort": 93,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 25,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                90,
                91,
                92,
                93,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                90,
                91,
                92,
                93,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                90,
                91,
                92,
                93,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                90,
                91,
                92,
                93,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                93
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "90": {
        "mapping": {
          "id": 90,
          "name": "eth1/23/2",
          "controllingPort": 94,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 26,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                94
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "91": {
        "mapping": {
          "id": 91,
          "name": "eth1/23/3",
          "controllingPort": 95,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 27,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                95
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "92": {
        "mapping": {
          "id": 92,
          "name": "eth1/23/4",
          "controllingPort": 96,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 28,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip23",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "93": {
        "mapping": {
          "id": 93,
          "name": "eth1/24/1",
          "controllingPort": 89,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 29,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                89,
                90,
                91,
                92,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                89,
                90,
                91,
                92,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                89,
                90,
                91,
                92,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                89,
                90,
                91,
                92,
                94,
                95,
                96
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                89
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "94": {
        "mapping": {
          "id": 94,
          "name": "eth1/24/2",
          "controllingPort": 93,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 30,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                90
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "95": {
        "mapping": {
          "id": 95,
          "name": "eth1/24/3",
          "controllingPort": 93,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 31,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                91
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "96": {
        "mapping": {
          "id": 96,
          "name": "eth1/24/4",
          "controllingPort": 93,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 5,
          "attachedCorePortIndex": 32,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                92
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core23",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip24",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "97": {
        "mapping": {
          "id": 97,
          "name": "eth1/25/1",
          "controllingPort": 101,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 25,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                98,
                99,
                100,
                101,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                98,
                99,
                100,
                101,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                98,
                99,
                100,
                101,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                98,
                99,
                100,
                101,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                101
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "98": {
        "mapping": {
          "id": 98,
          "name": "eth1/25/2",
          "controllingPort": 102,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 26,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                102
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "99": {
        "mapping": {
          "id": 99,
          "name": "eth1/25/3",
          "controllingPort": 103,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 27,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                103
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "100": {
        "mapping": {
          "id": 100,
          "name": "eth1/25/4",
          "controllingPort": 104,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 28,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip25",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "101": {
        "mapping": {
          "id": 101,
          "name": "eth1/26/1",
          "controllingPort": 97,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 29,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                97,
                98,
                99,
                100,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                97,
                98,
                99,
                100,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                97,
                98,
                99,
                100,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                97,
                98,
                99,
                100,
                102,
                103,
                104
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                97
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "102": {
        "mapping": {
          "id": 102,
          "name": "eth1/26/2",
          "controllingPort": 101,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 30,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                98
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "103": {
        "mapping": {
          "id": 103,
          "name": "eth1/26/3",
          "controllingPort": 101,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 31,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                99
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "104": {
        "mapping": {
          "id": 104,
          "name": "eth1/26/4",
          "controllingPort": 101,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 32,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                100
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core31",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip26",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "105": {
        "mapping": {
          "id": 105,
          "name": "eth1/27/1",
          "controllingPort": 109,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 17,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                106,
                107,
                108,
                109,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                106,
                107,
                108,
                109,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                106,
                107,
                108,
                109,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                106,
                107,
                108,
                109,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                109
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "106": {
        "mapping": {
          "id": 106,
          "name": "eth1/27/2",
          "controllingPort": 110,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 18,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                110
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "107": {
        "mapping": {
          "id": 107,
          "name": "eth1/27/3",
          "controllingPort": 111,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 19,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                111
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "108": {
        "mapping": {
          "id": 108,
          "name": "eth1/27/4",
          "controllingPort": 112,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 20,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip27",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "109": {
        "mapping": {
          "id": 109,
          "name": "eth1/28/1",
          "controllingPort": 105,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 21,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                105,
                106,
                107,
                108,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                105,
                106,
                107,
                108,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                105,
                106,
                107,
                108,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                105,
                106,
                107,
                108,
                110,
                111,
                112
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                105
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "110": {
        "mapping": {
          "id": 110,
          "name": "eth1/28/2",
          "controllingPort": 109,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 22,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                106
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "111": {
        "mapping": {
          "id": 111,
          "name": "eth1/28/3",
          "controllingPort": 109,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 23,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                107
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "112": {
        "mapping": {
          "id": 112,
          "name": "eth1/28/4",
          "controllingPort": 109,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 24,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                108
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core30",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip28",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "113": {
        "mapping": {
          "id": 113,
          "name": "eth1/29/1",
          "controllingPort": 117,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 9,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                114,
                115,
                116,
                117,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                114,
                115,
                116,
                117,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                114,
                115,
                116,
                117,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                114,
                115,
                116,
                117,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                117
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "114": {
        "mapping": {
          "id": 114,
          "name": "eth1/29/2",
          "controllingPort": 118,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 10,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                118
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "115": {
        "mapping": {
          "id": 115,
          "name": "eth1/29/3",
          "controllingPort": 119,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 11,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                119
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "116": {
        "mapping": {
          "id": 116,
          "name": "eth1/29/4",
          "controllingPort": 120,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 12,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip29",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "117": {
        "mapping": {
          "id": 117,
          "name": "eth1/30/1",
          "controllingPort": 113,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 13,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                113,
                114,
                115,
                116,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                113,
                114,
                115,
                116,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                113,
                114,
                115,
                116,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                113,
                114,
                115,
                116,
                118,
                119,
                120
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                113
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "118": {
        "mapping": {
          "id": 118,
          "name": "eth1/30/2",
          "controllingPort": 117,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 14,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                114
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "119": {
        "mapping": {
          "id": 119,
          "name": "eth1/30/3",
          "controllingPort": 117,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 15,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                115
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "120": {
        "mapping": {
          "id": 120,
          "name": "eth1/30/4",
          "controllingPort": 117,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 16,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                116
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core29",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip30",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "121": {
        "mapping": {
          "id": 121,
          "name": "eth1/31/1",
          "controllingPort": 125,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 1,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                122,
                123,
                124,
                125,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                122,
                123,
                124,
                125,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                122,
                123,
                124,
                125,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                122,
                123,
                124,
                125,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                125
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "122": {
        "mapping": {
          "id": 122,
          "name": "eth1/31/2",
          "controllingPort": 126,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 2,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                126
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "123": {
        "mapping": {
          "id": 123,
          "name": "eth1/31/3",
          "controllingPort": 127,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 3,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                127
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "124": {
        "mapping": {
          "id": 124,
          "name": "eth1/31/4",
          "controllingPort": 128,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 4,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip31",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    },
    "125": {
        "mapping": {
          "id": 125,
          "name": "eth1/32/1",
          "controllingPort": 121,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 0
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 0
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 1
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 2
                }
              }
            },
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 5,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "23": {
              "subsumedPorts": [
                121,
                122,
                123,
                124,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "25": {
              "subsumedPorts": [
                121,
                122,
                123,
                124,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "38": {
              "subsumedPorts": [
                121,
                122,
                123,
                124,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "45": {
              "subsumedPorts": [
                121,
                122,
                123,
                124,
                126,
                127,
                128
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 0
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 1
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 2
                    }
                  },
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 3
                    }
                  }
                ]
              }
          },
          "47": {
              "subsumedPorts": [
                121
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 0
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 0
                    }
                  }
                ]
              }
          }
        }
    },
    "126": {
        "mapping": {
          "id": 126,
          "name": "eth1/32/2",
          "controllingPort": 125,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 1
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 1
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 6,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                122
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 1
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 1
                    }
                  }
                ]
              }
          }
        }
    },
    "127": {
        "mapping": {
          "id": 127,
          "name": "eth1/32/3",
          "controllingPort": 125,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 2
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 2
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 7,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                123
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 2
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 2
                    }
                  }
                ]
              }
          }
        }
    },
    "128": {
        "mapping": {
          "id": 128,
          "name": "eth1/32/4",
          "controllingPort": 125,
          "pins": [
            {
              "a": {
                "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                "lane": 3
              },
              "z": {
                "end": {
                  "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                  "lane": 3
                }
              }
            }
          ],
          "portType": 0,
          "attachedCoreId": 7,
          "attachedCorePortIndex": 8,
          "virtualDeviceId": 0,
          "scope": 1
        },
        "supportedProfiles": {
          "47": {
              "subsumedPorts": [
                124
              ],
              "pins": {
                "iphy": [
                  {
                    "id": {
                      "chip": "NPU-Q4D_NIF-slot1/chip1/core28",
                      "lane": 3
                    }
                  }
                ],
                "transceiver": [
                  {
                    "id": {
                      "chip": "TRANSCEIVER-QSFP28-slot1/chip32",
                      "lane": 3
                    }
                  }
                ]
              }
          }
        }
    }
  },
  "chips": [
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core0",
      "type": 1,
      "physicalID": 0
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core1",
      "type": 1,
      "physicalID": 1
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core2",
      "type": 1,
      "physicalID": 2
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core3",
      "type": 1,
      "physicalID": 3
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core8",
      "type": 1,
      "physicalID": 8
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core9",
      "type": 1,
      "physicalID": 9
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core10",
      "type": 1,
      "physicalID": 10
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core11",
      "type": 1,
      "physicalID": 11
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core20",
      "type": 1,
      "physicalID": 20
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core21",
      "type": 1,
      "physicalID": 21
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core22",
      "type": 1,
      "physicalID": 22
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core23",
      "type": 1,
      "physicalID": 23
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core28",
      "type": 1,
      "physicalID": 28
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core29",
      "type": 1,
      "physicalID": 29
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core30",
      "type": 1,
      "physicalID": 30
    },
    {
      "name": "NPU-Q4D_NIF-slot1/chip1/core31",
      "type": 1,
      "physicalID": 31
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip1",
      "type": 3,
      "physicalID": 0
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip2",
      "type": 3,
      "physicalID": 1
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip3",
      "type": 3,
      "physicalID": 2
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip4",
      "type": 3,
      "physicalID": 3
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip5",
      "type": 3,
      "physicalID": 4
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip6",
      "type": 3,
      "physicalID": 5
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip7",
      "type": 3,
      "physicalID": 6
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip8",
      "type": 3,
      "physicalID": 7
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip9",
      "type": 3,
      "physicalID": 8
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip10",
      "type": 3,
      "physicalID": 9
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip11",
      "type": 3,
      "physicalID": 10
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip12",
      "type": 3,
      "physicalID": 11
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip13",
      "type": 3,
      "physicalID": 12
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip14",
      "type": 3,
      "physicalID": 13
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip15",
      "type": 3,
      "physicalID": 14
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip16",
      "type": 3,
      "physicalID": 15
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip17",
      "type": 3,
      "physicalID": 16
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip18",
      "type": 3,
      "physicalID": 17
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip19",
      "type": 3,
      "physicalID": 18
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip20",
      "type": 3,
      "physicalID": 19
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip21",
      "type": 3,
      "physicalID": 20
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip22",
      "type": 3,
      "physicalID": 21
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip23",
      "type": 3,
      "physicalID": 22
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip24",
      "type": 3,
      "physicalID": 23
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip25",
      "type": 3,
      "physicalID": 24
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip26",
      "type": 3,
      "physicalID": 25
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip27",
      "type": 3,
      "physicalID": 26
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip28",
      "type": 3,
      "physicalID": 27
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip29",
      "type": 3,
      "physicalID": 28
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip30",
      "type": 3,
      "physicalID": 29
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip31",
      "type": 3,
      "physicalID": 30
    },
    {
      "name": "TRANSCEIVER-QSFP28-slot1/chip32",
      "type": 3,
      "physicalID": 31
    }
  ],
  "platformSupportedProfiles": [
    {
      "factor": {
        "profileID": 38
      },
      "profile": {
        "speed": 400000,
        "iphy": {
          "numLanes": 4,
          "modulation": 2,
          "fec": 11,
          "medium": 2,
          "interfaceType": 41
        }
      }
    },
    {
      "factor": {
        "profileID": 45
      },
      "profile": {
        "speed": 400000,
        "iphy": {
          "numLanes": 4,
          "modulation": 2,
          "fec": 11,
          "medium": 1,
          "interfaceType": 12
        }
      }
    },
    {
      "factor": {
        "profileID": 47
      },
      "profile": {
        "speed": 100000,
        "iphy": {
          "numLanes": 1,
          "modulation": 2,
          "fec": 544,
          "medium": 2,
          "interfaceType": 41
        }
      }
    },
    {
      "factor": {
        "profileID": 23
      },
      "profile": {
        "speed": 100000,
        "iphy": {
          "numLanes": 4,
          "modulation": 1,
          "fec": 528,
          "medium": 2,
          "interfaceType": 21
        }
      }
    },
    {
      "factor": {
        "profileID": 25
      },
      "profile": {
        "speed": 200000,
        "iphy": {
          "numLanes": 4,
          "modulation": 2,
          "fec": 11,
          "medium": 2,
          "interfaceType": 41
        }
      }
    }
  ]
}
)";

} // namespace

namespace facebook::fboss {
Nh5010fPlatformMapping::Nh5010fPlatformMapping()
    : PlatformMapping(kJsonPlatformMappingStr) {}

Nh5010fPlatformMapping::Nh5010fPlatformMapping(
    const std::string& platformMappingStr)
    : PlatformMapping(platformMappingStr) {}

} // namespace facebook::fboss
