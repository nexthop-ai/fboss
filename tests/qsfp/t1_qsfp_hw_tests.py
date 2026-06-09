# Passing QSFP HW tests for wdg104 (Wedge800BACT)
# wedge800bnhp/physdk-credo-0.7.2/credo-0.7.2
# Config: wedge800bact.materialized_JSON
#
# Set QSFP_CONFIG environment variable to override the default config
#   export QSFP_CONFIG=./share/qsfp_test_configs/wedge800bact.materialized_JSON
#
# commented out tests are t0 tests and are not run due to duplication

test_context = {
    "filters": [
        # Basic init
        "EmptyHwTest.CheckInit",

        # Config
        "HwTransceiverConfigTest.moduleConfigVerification",

        # Stats tests
        "HwTest.publishStats",
        "HwTest.transceiverIOStats",

        # Transceiver info tests
        "HwTest.CheckTcvrNameAndInterfaces",

        # Fw tests
        "HwTest.checkCmisModuleFirmwareUpgradeCdbTimeout",

        # I2C tests
        # "HwTest.i2cStressRead",
        # "HwTest.i2cStressWrite",
        "HwTest.i2cLogCapacityRead",
        "HwTest.i2cLogCapacityWrite",
        "HwTest.cmisPageChange",
        "HwTest.i2cUniqueSerialNumbers",

        # CMIS
        # HwTest.cmisPageChange

        # Reset tests
        # "HwTransceiverResetTest.resetTranscieverAndDetectPresence",
        "HwTransceiverResetTest.resetTranscieverAndDetectStateChanged",
        "HwTransceiverResetTest.verifyHardResetAction",
        # "HwTransceiverResetBmcLiteTest.verifyResetControl",

        # State machine tests
        "HwStateMachineTestWithoutIphyProgramming.CheckOpticsDetection",
        # "HwStateMachineTest.CheckPortsProgrammed",
        "HwStateMachineTest.CheckPortStatusUpdated",
        "HwStateMachineTest.CheckTransceiverRemoved",
        "HwStateMachineTest.CheckAgentConfigChanged",
    ],
}


def test_t1_qsfp_hw_passing(qsfp_test_runner):
    assert qsfp_test_runner.run_test(test_context)
