import pyrtl

main_memory = pyrtl.MemBlock(bitwidth=32, addrwidth=32, name="main_mem")

virtual_addr_i        = pyrtl.Input(bitwidth=32, name="virtual_addr_i")
new_req_i             = pyrtl.Input(bitwidth=1,  name="new_req_i")
reset_i               = pyrtl.Input(bitwidth=1,  name="reset_i")
req_type_i            = pyrtl.Input(bitwidth=1,  name="req_type_i")

physical_addr_o       = pyrtl.Output(bitwidth=32,name="physical_addr_o")
dirty_o               = pyrtl.Output(bitwidth=1, name="dirty_o")
valid_o               = pyrtl.Output(bitwidth=1, name="valid_o")
ref_o                 = pyrtl.Output(bitwidth=1, name="ref_o")
error_code_o          = pyrtl.Output(bitwidth=3, name="error_code_o")
finished_walk_o       = pyrtl.Output(bitwidth=1, name="finished_walk_o")
# readable_o            = pyrtl.Output(bitwidth=1, name="readable_o")
# writable_o            = pyrtl.Output(bitwidth=1, name="writable_o")

page_fault          = pyrtl.WireVector(bitwidth=1, name="page_fault")
state               = pyrtl.Register(bitwidth=2, name="state")
base_register       = pyrtl.Const(0x3FFBFF, bitwidth=22)

# Step 1 : Split input into the three offsets
offset1 = pyrtl.WireVector(bitwidth=10, name="offset1")
offset2 = pyrtl.WireVector(bitwidth=10, name="offset2")
offset3 = pyrtl.WireVector(bitwidth=12, name="offset3")
offset1 |= virtual_addr_i[22:32]
offset2 |= virtual_addr_i[12:22]
offset3 |= virtual_addr_i[0:12]


# Step 2 : UPDATE STATE according to state diagram in instructions
with pyrtl.conditional_assignment:
    with reset_i == 0:
        with state == 0:
            with new_req_i == 1:
                state.next |= 1
        with state == 1:
            with page_fault == 1:
                state.next |= 0
            with page_fault == 0:
                state.next |= 2
        with state == 2:
            state.next |= 0

# Step 3 : Determine physical address by walking the page table structure
next_addr = pyrtl.Register(bitwidth=32, name="temp_addr")
with pyrtl.conditional_assignment:
    with state == 0:
        next_addr.next |= pyrtl.corecircuits.concat(base_register, offset1)
        # print(temp_addr.bitwidth)
        
    with state == 1:
        temp_addr = main_memory[next_addr]
        
        valid = temp_addr[31]
        valid_o |= temp_addr[31]
        dirty_o |= temp_addr[30]
        ref_o |= temp_addr[29]
        
        with valid == 0:
            page_fault |= 1
        next_addr.next |= pyrtl.corecircuits.concat(temp_addr[0:22], offset2)
        # print(temp_addr.bitwidth)
        
    with state == 2:
        temp_addr = main_memory[next_addr]
        
        valid_o |= temp_addr[31]
        dirty_o |= temp_addr[30]
        ref_o |= temp_addr[29]
        writable = temp_addr[28]
        readable = temp_addr[27]
        
        # writable_o |= temp_addr[28]
        # readable_o |= temp_addr[27]
        
        valid = temp_addr[31]
        with valid == 0:
            page_fault |= 1
        temp_addr2 = pyrtl.corecircuits.concat(temp_addr[0:20], offset3)
        # print(temp_addr.bitwidth)
        # temp_addr = temp_addr | offset3
        physical_addr_o |= temp_addr2
        
            

# Step 4 : Determine the outputs based on the last level of the page table walk
with pyrtl.conditional_assignment:
    with reset_i == 0:
        with state == 0:
            error_code_o |= 0
        with state == 1:
            with page_fault == 1:
                error_code_o |= 1
            with page_fault == 0:
                error_code_o |= 0
        with state == 2:
            finished_walk_o |= 1
            with page_fault == 1:
                error_code_o |= 1
            with req_type_i == 0:
                with readable == 0:
                    error_code_o |= 2
            with req_type_i == 1:
                with writable == 0:
                    error_code_o |= 4
                

                

if __name__ == "__main__":

    """
    These memory addresses correspond to the test that we walk through in the instructions
    This just does a basic walk from the first level to the last level where no errors should occur
    """
    memory = {
        4293918528: 0xC43FFC6B,
        4294029192: 0xAC061D26,
        1641180595: 0xDEADBEEF
    }

    sim_trace = pyrtl.SimulationTrace()
    sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={main_memory: memory})

    for i in range(3):
        sim.step({
            new_req_i: 1,
            reset_i: 0,
            virtual_addr_i: 0xD0388DB3,
            req_type_i: 0
    })

    sim_trace.render_trace(symbol_len=20)

    assert (sim_trace.trace["physical_addr_o"][-1] == 0x61d26db3)
    assert (sim_trace.trace["error_code_o"][-1] == 0x0)
    assert (sim_trace.trace["dirty_o"][-1] == 0x0)
    # assert (sim_trace.trace["readable_o"][-1] == 0x1)
    
    # memory = {
    #     4293918528: 0x00000000,  # Level 1 entry is invalid (page fault)
    # }

    # sim_trace = pyrtl.SimulationTrace()
    # sim = pyrtl.Simulation(tracer=sim_trace, memory_value_map={main_memory: memory})

    # for i in range(3):
    #     sim.step({
    #         new_req_i: 1,
    #         reset_i: 0,
    #         virtual_addr_i: 0xA1234567,  # Address that causes a page fault
    #         req_type_i: 0
    #     })

    # sim_trace.render_trace(symbol_len=20)

    # assert (sim_trace.trace["physical_addr_o"][-1] == 0x0)  # No valid physical address
    # assert (sim_trace.trace["error_code_o"][-1] == 0x1)  # Page fault error
    # assert (sim_trace.trace["dirty_o"][-1] == 0x0)  # No dirty bit set
    # # assert (sim_trace.trace["readable_o"][-1] == 0x0
    
